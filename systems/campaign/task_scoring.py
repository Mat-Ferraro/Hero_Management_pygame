from __future__ import annotations

from typing import Any, Dict, List

from systems.progression.hero_abilities import apply_party_ability_modifiers
from systems.progression.hero_career import effective_stat


DISPATCH_STATS = ["might", "guard", "wit", "presence", "swift"]

CLASS_DISPATCH_BONUSES: Dict[str, Dict[str, int]] = {
    "Warrior": {"might": 1, "guard": 1},
    "Rogue": {"swift": 1, "wit": 1},
    "Cleric": {"guard": 1, "presence": 1},
    "Mage": {"wit": 2},
}

SUBCLASS_DISPATCH_BONUSES: Dict[str, Dict[str, int]] = {
    "vanguard": {"might": 1, "swift": 1},
    "warden": {"guard": 2},
    "captain": {"presence": 1, "guard": 1},
    "scout": {"swift": 2},
    "fixer": {"presence": 1, "wit": 1},
    "oracle": {"wit": 1, "presence": 1},
    "templar": {"guard": 1, "might": 1},
    "arcanist": {"wit": 2},
    "seer": {"wit": 1, "swift": 1},
    "spellblade": {"might": 1, "wit": 1},
}

OUTCOME_PROFILES: Dict[str, Dict[str, float]] = {
    "great_success": {
        "injury_chance": 0.00,
        "extra_rest_min": 0.0,
        "extra_rest_max": 0.0,
        "satisfaction_delta": 2,
        "payout_multiplier": 1.25,
        "xp_multiplier": 1.20,
    },
    "success": {
        "injury_chance": 0.08,
        "extra_rest_min": 3.0,
        "extra_rest_max": 6.0,
        "satisfaction_delta": 1,
        "payout_multiplier": 1.00,
        "xp_multiplier": 1.00,
    },
    "partial_success": {
        "injury_chance": 0.30,
        "extra_rest_min": 6.0,
        "extra_rest_max": 12.0,
        "satisfaction_delta": -1,
        "payout_multiplier": 0.65,
        "xp_multiplier": 0.75,
    },
    "critical_failure": {
        "injury_chance": 0.65,
        "extra_rest_min": 12.0,
        "extra_rest_max": 22.0,
        "satisfaction_delta": -3,
        "payout_multiplier": 0.00,
        "xp_multiplier": 0.35,
    },
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _int_dict_with_default() -> Dict[str, int]:
    return {stat: 0 for stat in DISPATCH_STATS}


def _apply_bonus_map(target: Dict[str, int], bonuses: Dict[str, int]) -> None:
    for stat_name, bonus_value in bonuses.items():
        if stat_name in target:
            target[stat_name] += int(bonus_value)


def hero_dispatch_stats(hero) -> Dict[str, int]:
    hero_class = getattr(hero, "hero_class", "")
    subclass = (getattr(hero, "subclass", None) or "").lower()

    might_value = effective_stat(hero, "might")
    agility_value = effective_stat(hero, "agility")
    mind_value = effective_stat(hero, "mind")
    spirit_value = effective_stat(hero, "spirit")

    stats = {
        "might": might_value,
        "guard": max(0, int(round((might_value + spirit_value) / 2))),
        "wit": mind_value,
        "presence": spirit_value,
        "swift": agility_value,
    }

    _apply_bonus_map(stats, CLASS_DISPATCH_BONUSES.get(hero_class, {}))

    for subclass_key, bonus_map in SUBCLASS_DISPATCH_BONUSES.items():
        if subclass_key in subclass:
            _apply_bonus_map(stats, bonus_map)

    return stats


def combined_party_dispatch_stats(heroes: List[Any]) -> Dict[str, int]:
    totals = _int_dict_with_default()

    for hero in heroes:
        hero_stats = hero_dispatch_stats(hero)
        for stat_name in DISPATCH_STATS:
            totals[stat_name] += int(hero_stats.get(stat_name, 0))

    return totals


def _minimum_rule(target: int) -> Dict[str, Any]:
    return {"mode": "minimum", "target": max(0, int(target))}


def normalize_rule(rule: Dict[str, Any] | None) -> Dict[str, Any]:
    if not rule:
        return _minimum_rule(0)

    mode = str(rule.get("mode", "minimum")).lower()

    if mode == "range":
        min_value = max(0, int(rule.get("min", 0)))
        max_value = max(min_value, int(rule.get("max", min_value)))
        return {"mode": "range", "min": min_value, "max": max_value}

    if mode == "maximum":
        return {"mode": "maximum", "target": max(0, int(rule.get("target", 0)))}

    return {"mode": "minimum", "target": max(0, int(rule.get("target", 0)))}


def get_task_stat_rules(task) -> Dict[str, Dict[str, Any]]:
    explicit_rules = dict(getattr(task, "stat_rules", {}) or {})
    required_stats = dict(getattr(task, "required_stats", {}) or {})

    rules: Dict[str, Dict[str, Any]] = {}
    for stat_name in DISPATCH_STATS:
        if stat_name in explicit_rules:
            rules[stat_name] = normalize_rule(explicit_rules[stat_name])
        else:
            rules[stat_name] = _minimum_rule(required_stats.get(stat_name, 0))

    return rules


def stat_rule_has_weight(rule: Dict[str, Any]) -> bool:
    mode = str(rule.get("mode", "minimum"))

    if mode == "minimum":
        return int(rule.get("target", 0)) > 0
    if mode == "range":
        return int(rule.get("max", 0)) > 0
    if mode == "maximum":
        return int(rule.get("target", 0)) > 0

    return False


def evaluate_stat_rule(value: int, rule: Dict[str, Any]) -> Dict[str, Any]:
    value = max(0, int(value))
    rule = normalize_rule(rule)
    mode = rule["mode"]

    if mode == "minimum":
        target = max(0, int(rule.get("target", 0)))
        if target <= 0:
            return {"score": 1.0, "mode": mode}
        return {"score": _clamp(value / target, 0.0, 1.0), "mode": mode}

    if mode == "range":
        min_value = max(0, int(rule.get("min", 0)))
        max_value = max(min_value, int(rule.get("max", min_value)))

        if min_value <= value <= max_value:
            return {"score": 1.0, "mode": mode}

        if value < min_value:
            if min_value <= 0:
                return {"score": 1.0, "mode": mode}
            return {"score": _clamp(value / min_value, 0.0, 1.0), "mode": mode}

        if value > max_value:
            if value <= 0:
                return {"score": 1.0, "mode": mode}
            return {"score": _clamp(max_value / value, 0.0, 1.0), "mode": mode}

    if mode == "maximum":
        target = max(0, int(rule.get("target", 0)))

        if value <= target:
            return {"score": 1.0, "mode": mode}

        if value <= 0:
            return {"score": 1.0, "mode": mode}

        if target <= 0:
            return {"score": 0.0, "mode": mode}

        return {"score": _clamp(target / value, 0.0, 1.0), "mode": mode}

    return {"score": 0.0, "mode": mode}


def format_stat_rule_short(rule: Dict[str, Any]) -> str:
    rule = normalize_rule(rule)
    mode = rule["mode"]

    if mode == "minimum":
        return f"Need {int(rule.get('target', 0))}+"
    if mode == "range":
        return f"Best {int(rule.get('min', 0))}-{int(rule.get('max', 0))}"
    if mode == "maximum":
        return f"Keep ≤{int(rule.get('target', 0))}"
    return "Any"


def preferred_class_bonus(task, heroes: List[Any]) -> float:
    preferred = set(getattr(task, "preferred_classes", []) or [])
    if not preferred:
        return 0.0

    matches = sum(1 for hero in heroes if getattr(hero, "hero_class", None) in preferred)
    if matches <= 0:
        return 0.0

    return min(0.15, matches * 0.05)


def party_size_bonus(task, heroes: List[Any]) -> float:
    max_heroes = max(1, int(getattr(task, "max_heroes", 1)))
    if not heroes:
        return 0.0

    fill_ratio = min(1.0, len(heroes) / max_heroes)
    return fill_ratio * 0.05


def outcome_band_from_fit_and_roll(success_chance: float, fit_score: float, roll_value: float) -> str:
    success_chance = _clamp(success_chance, 0.0, 1.0)
    fit_score = _clamp(fit_score, 0.0, 1.0)
    roll_value = _clamp(roll_value, 0.0, 1.0)

    if roll_value <= success_chance:
        if fit_score >= 0.90 and roll_value <= success_chance * 0.65:
            return "great_success"
        return "success"

    if fit_score >= 0.45:
        return "partial_success"

    return "critical_failure"


def outcome_profile(outcome_band: str) -> Dict[str, float]:
    return dict(OUTCOME_PROFILES.get(outcome_band, OUTCOME_PROFILES["critical_failure"]))


def injury_profile_for_band(outcome_band: str) -> Dict[str, float]:
    profile = outcome_profile(outcome_band)
    return {
        "injury_chance": float(profile["injury_chance"]),
        "extra_rest_min": float(profile["extra_rest_min"]),
        "extra_rest_max": float(profile["extra_rest_max"]),
    }


def satisfaction_delta_for_band(outcome_band: str) -> int:
    profile = outcome_profile(outcome_band)
    return int(profile["satisfaction_delta"])


def payout_multiplier_for_band(outcome_band: str) -> float:
    profile = outcome_profile(outcome_band)
    return float(profile["payout_multiplier"])


def xp_multiplier_for_band(outcome_band: str) -> float:
    profile = outcome_profile(outcome_band)
    return float(profile["xp_multiplier"])


def calculate_task_success_chance(task, heroes: List[Any]) -> Dict[str, Any]:
    provided = combined_party_dispatch_stats(heroes)
    stat_rules = get_task_stat_rules(task)

    active_stats: List[str] = []
    stat_breakdown: Dict[str, Dict[str, Any]] = {}

    for stat_name in DISPATCH_STATS:
        rule = stat_rules[stat_name]
        score_data = evaluate_stat_rule(provided.get(stat_name, 0), rule)
        has_weight = stat_rule_has_weight(rule)

        stat_breakdown[stat_name] = {
            "rule": rule,
            "provided": int(provided.get(stat_name, 0)),
            "score": float(score_data["score"]),
            "weighted": has_weight,
        }

        if has_weight:
            active_stats.append(stat_name)

    if active_stats:
        fit_score = sum(stat_breakdown[stat]["score"] for stat in active_stats) / len(active_stats)
    else:
        fit_score = 1.0

    success_chance = fit_score
    success_chance += preferred_class_bonus(task, heroes)
    success_chance += party_size_bonus(task, heroes)

    ability_data = apply_party_ability_modifiers(task, heroes)
    success_chance += float(ability_data["success_bonus"])
    success_chance = _clamp(success_chance, 0.0, 1.0)

    return {
        "required_stats": dict(getattr(task, "required_stats", {}) or {}),
        "stat_rules": stat_rules,
        "provided_stats": provided,
        "stat_breakdown": stat_breakdown,
        "fit_score": fit_score,
        "success_chance": success_chance,
        "ability_modifiers": ability_data,
    }


def resolve_task_outcome_from_chance(task, heroes: List[Any], roll_value: float) -> Dict[str, Any]:
    chance_data = calculate_task_success_chance(task, heroes)
    fit_score = float(chance_data["fit_score"])
    success_chance = float(chance_data["success_chance"])
    roll_value = _clamp(roll_value, 0.0, 1.0)

    outcome_band = outcome_band_from_fit_and_roll(
        success_chance=success_chance,
        fit_score=fit_score,
        roll_value=roll_value,
    )

    ability_data = dict(chance_data.get("ability_modifiers", {}) or {})
    base_injury_profile = injury_profile_for_band(outcome_band)

    injury_profile = {
        "injury_chance": _clamp(
            float(base_injury_profile["injury_chance"]) * float(ability_data.get("injury_multiplier", 1.0)),
            0.0,
            1.0,
        ),
        "extra_rest_min": float(base_injury_profile["extra_rest_min"]),
        "extra_rest_max": float(base_injury_profile["extra_rest_max"]),
    }

    satisfaction_delta = satisfaction_delta_for_band(outcome_band) + int(
        ability_data.get("satisfaction_bonus", 0)
    )

    chance_data.update(
        {
            "roll_value": roll_value,
            "outcome_band": outcome_band,
            "payout_multiplier": payout_multiplier_for_band(outcome_band),
            "xp_multiplier": xp_multiplier_for_band(outcome_band),
            "injury_profile": injury_profile,
            "satisfaction_delta": satisfaction_delta,
        }
    )
    return chance_data


def format_dispatch_stats(stats: Dict[str, int]) -> str:
    return (
        f"M {stats.get('might', 0)} | "
        f"G {stats.get('guard', 0)} | "
        f"W {stats.get('wit', 0)} | "
        f"P {stats.get('presence', 0)} | "
        f"S {stats.get('swift', 0)}"
    )