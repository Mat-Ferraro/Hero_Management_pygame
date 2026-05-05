from __future__ import annotations

from typing import Dict, List

from systems.hero_abilities import apply_party_ability_modifiers
from systems.hero_career import effective_stat

DISPATCH_STATS = ["might", "guard", "wit", "presence", "swift"]


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

    if hero_class == "Warrior":
        stats["might"] += 1
        stats["guard"] += 1
    elif hero_class == "Rogue":
        stats["swift"] += 1
        stats["wit"] += 1
    elif hero_class == "Cleric":
        stats["guard"] += 1
        stats["presence"] += 1
    elif hero_class == "Mage":
        stats["wit"] += 2

    if "vanguard" in subclass:
        stats["might"] += 1
        stats["swift"] += 1
    elif "warden" in subclass:
        stats["guard"] += 2
    elif "captain" in subclass:
        stats["presence"] += 1
        stats["guard"] += 1
    elif "scout" in subclass:
        stats["swift"] += 2
    elif "fixer" in subclass:
        stats["presence"] += 1
        stats["wit"] += 1
    elif "oracle" in subclass:
        stats["wit"] += 1
        stats["presence"] += 1
    elif "templar" in subclass:
        stats["guard"] += 1
        stats["might"] += 1
    elif "arcanist" in subclass:
        stats["wit"] += 2
    elif "seer" in subclass:
        stats["wit"] += 1
        stats["swift"] += 1
    elif "spellblade" in subclass:
        stats["might"] += 1
        stats["wit"] += 1

    return stats


def combined_party_dispatch_stats(heroes: List) -> Dict[str, int]:
    totals = {stat: 0 for stat in DISPATCH_STATS}

    for hero in heroes:
        hero_stats = hero_dispatch_stats(hero)
        for stat in DISPATCH_STATS:
            totals[stat] += int(hero_stats.get(stat, 0))

    return totals


def _minimum_rule(target: int) -> Dict:
    return {"mode": "minimum", "target": max(0, int(target))}


def normalize_rule(rule: Dict | None) -> Dict:
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


def get_task_stat_rules(task) -> Dict[str, Dict]:
    explicit_rules = dict(getattr(task, "stat_rules", {}) or {})
    required_stats = dict(getattr(task, "required_stats", {}) or {})

    rules = {}
    for stat_name in DISPATCH_STATS:
        if stat_name in explicit_rules:
            rules[stat_name] = normalize_rule(explicit_rules[stat_name])
        else:
            rules[stat_name] = _minimum_rule(required_stats.get(stat_name, 0))

    return rules


def stat_rule_has_weight(rule: Dict) -> bool:
    mode = rule["mode"]

    if mode == "minimum":
        return int(rule.get("target", 0)) > 0
    if mode == "range":
        return int(rule.get("max", 0)) > 0
    if mode == "maximum":
        return int(rule.get("target", 0)) > 0

    return False


def evaluate_stat_rule(value: int, rule: Dict) -> Dict:
    value = max(0, int(value))
    rule = normalize_rule(rule)
    mode = rule["mode"]

    if mode == "minimum":
        target = max(0, int(rule.get("target", 0)))
        if target <= 0:
            return {"score": 1.0, "mode": mode}
        return {"score": max(0.0, min(1.0, value / target)), "mode": mode}

    if mode == "range":
        min_value = max(0, int(rule.get("min", 0)))
        max_value = max(min_value, int(rule.get("max", min_value)))

        if min_value <= value <= max_value:
            return {"score": 1.0, "mode": mode}

        if value < min_value:
            if min_value <= 0:
                return {"score": 1.0, "mode": mode}
            return {"score": max(0.0, min(1.0, value / min_value)), "mode": mode}

        if value > max_value:
            if value <= 0:
                return {"score": 1.0, "mode": mode}
            return {"score": max(0.0, min(1.0, max_value / value)), "mode": mode}

    if mode == "maximum":
        target = max(0, int(rule.get("target", 0)))

        if value <= target:
            return {"score": 1.0, "mode": mode}

        if value <= 0:
            return {"score": 1.0, "mode": mode}

        if target <= 0:
            return {"score": 0.0, "mode": mode}

        return {"score": max(0.0, min(1.0, target / value)), "mode": mode}

    return {"score": 0.0, "mode": mode}


def format_stat_rule_short(rule: Dict) -> str:
    rule = normalize_rule(rule)
    mode = rule["mode"]

    if mode == "minimum":
        return f"Need {int(rule.get('target', 0))}+"
    if mode == "range":
        return f"Best {int(rule.get('min', 0))}-{int(rule.get('max', 0))}"
    if mode == "maximum":
        return f"Keep ≤{int(rule.get('target', 0))}"
    return "Any"


def preferred_class_bonus(task, heroes: List) -> float:
    preferred = set(getattr(task, "preferred_classes", []))
    if not preferred:
        return 0.0

    matches = 0
    for hero in heroes:
        if getattr(hero, "hero_class", None) in preferred:
            matches += 1

    if matches <= 0:
        return 0.0

    return min(0.15, matches * 0.05)


def party_size_bonus(task, heroes: List) -> float:
    max_heroes = max(1, int(getattr(task, "max_heroes", 1)))
    if not heroes:
        return 0.0

    fill_ratio = min(1.0, len(heroes) / max_heroes)
    return fill_ratio * 0.05


def outcome_band_from_fit_and_roll(success_chance: float, fit_score: float, roll_value: float) -> str:
    success_chance = max(0.0, min(1.0, float(success_chance)))
    fit_score = max(0.0, min(1.0, float(fit_score)))
    roll_value = max(0.0, min(1.0, float(roll_value)))

    if roll_value <= success_chance:
        if fit_score >= 0.90 and roll_value <= success_chance * 0.65:
            return "great_success"
        return "success"

    if fit_score >= 0.45:
        return "partial_success"

    return "critical_failure"


def injury_profile_for_band(outcome_band: str) -> Dict[str, float]:
    if outcome_band == "great_success":
        return {"injury_chance": 0.00, "extra_rest_min": 0.0, "extra_rest_max": 0.0}
    if outcome_band == "success":
        return {"injury_chance": 0.08, "extra_rest_min": 3.0, "extra_rest_max": 6.0}
    if outcome_band == "partial_success":
        return {"injury_chance": 0.30, "extra_rest_min": 6.0, "extra_rest_max": 12.0}
    return {"injury_chance": 0.65, "extra_rest_min": 12.0, "extra_rest_max": 22.0}


def satisfaction_delta_for_band(outcome_band: str) -> int:
    if outcome_band == "great_success":
        return 2
    if outcome_band == "success":
        return 1
    if outcome_band == "partial_success":
        return -1
    return -3


def payout_multiplier_for_band(outcome_band: str) -> float:
    if outcome_band == "great_success":
        return 1.25
    if outcome_band == "success":
        return 1.00
    if outcome_band == "partial_success":
        return 0.65
    return 0.0


def xp_multiplier_for_band(outcome_band: str) -> float:
    if outcome_band == "great_success":
        return 1.20
    if outcome_band == "success":
        return 1.00
    if outcome_band == "partial_success":
        return 0.75
    return 0.35


def calculate_task_success_chance(task, heroes: List) -> Dict:
    provided = combined_party_dispatch_stats(heroes)
    stat_rules = get_task_stat_rules(task)

    active_stats = []
    stat_breakdown = {}

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

    success_chance = max(0.0, min(1.0, success_chance))

    return {
        "required_stats": dict(getattr(task, "required_stats", {}) or {}),
        "stat_rules": stat_rules,
        "provided_stats": provided,
        "stat_breakdown": stat_breakdown,
        "fit_score": fit_score,
        "success_chance": success_chance,
        "ability_modifiers": ability_data,
    }


def resolve_task_outcome_from_chance(task, heroes: List, roll_value: float) -> Dict:
    chance_data = calculate_task_success_chance(task, heroes)
    fit_score = float(chance_data["fit_score"])
    success_chance = float(chance_data["success_chance"])
    roll_value = max(0.0, min(1.0, float(roll_value)))

    outcome_band = outcome_band_from_fit_and_roll(
        success_chance=success_chance,
        fit_score=fit_score,
        roll_value=roll_value,
    )

    ability_data = dict(chance_data.get("ability_modifiers", {}) or {})

    injury_profile = injury_profile_for_band(outcome_band)
    injury_profile = {
        "injury_chance": max(0.0, min(1.0, float(injury_profile["injury_chance"]) * float(ability_data.get("injury_multiplier", 1.0)))),
        "extra_rest_min": float(injury_profile["extra_rest_min"]),
        "extra_rest_max": float(injury_profile["extra_rest_max"]),
    }

    satisfaction_delta = satisfaction_delta_for_band(outcome_band) + int(ability_data.get("satisfaction_bonus", 0))

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