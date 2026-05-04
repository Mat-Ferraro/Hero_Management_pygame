from __future__ import annotations

from typing import Dict, List


DISPATCH_STATS = ["might", "guard", "wit", "presence", "swift"]
MAX_TOTAL_SUCCESS_BONUS = 0.15
MAX_TOTAL_SATISFACTION_BONUS = 2
MIN_INJURY_MULTIPLIER = 0.65


def _rule_mode(task, stat_name: str) -> str:
    stat_rules = dict(getattr(task, "stat_rules", {}) or {})
    rule = dict(stat_rules.get(stat_name, {}) or {})
    return str(rule.get("mode", "minimum")).lower()


def _rule_target(task, stat_name: str) -> int:
    stat_rules = dict(getattr(task, "stat_rules", {}) or {})
    rule = dict(stat_rules.get(stat_name, {}) or {})
    return int(rule.get("target", 0))


def _rule_min(task, stat_name: str) -> int:
    stat_rules = dict(getattr(task, "stat_rules", {}) or {})
    rule = dict(stat_rules.get(stat_name, {}) or {})
    return int(rule.get("min", 0))


def _rule_max(task, stat_name: str) -> int:
    stat_rules = dict(getattr(task, "stat_rules", {}) or {})
    rule = dict(stat_rules.get(stat_name, {}) or {})
    return int(rule.get("max", _rule_min(task, stat_name)))


def _task_has_maximum_rules(task) -> bool:
    stat_rules = dict(getattr(task, "stat_rules", {}) or {})
    for rule in stat_rules.values():
        if str(rule.get("mode", "minimum")).lower() == "maximum":
            return True
    return False


def _task_values_stat(task, stat_name: str, threshold: int = 4) -> bool:
    mode = _rule_mode(task, stat_name)
    if mode == "minimum":
        return _rule_target(task, stat_name) >= threshold
    if mode == "range":
        return _rule_max(task, stat_name) >= threshold
    if mode == "maximum":
        return _rule_target(task, stat_name) >= threshold
    return False


def _task_is_mixed_might_wit(task) -> bool:
    return _task_values_stat(task, "might", 3) and _task_values_stat(task, "wit", 3)


def _hero_subclasses(hero) -> List[str]:
    values = []
    active = getattr(hero, "subclass", None)
    if active:
        values.append(str(active))

    unlocked = list(getattr(hero, "unlocked_subclasses", []) or [])
    for item in unlocked:
        text = str(item)
        if text not in values:
            values.append(text)

    return values


def apply_party_ability_modifiers(task, heroes: List) -> Dict:
    success_bonus = 0.0
    injury_multiplier = 1.0
    satisfaction_bonus = 0
    notes: List[str] = []

    for hero in heroes:
        hero_name = getattr(hero, "name", "Hero")

        for subclass in _hero_subclasses(hero):
            name = subclass.lower()

            if name == "vanguard" and _task_values_stat(task, "might", 4):
                success_bonus += 0.04
                notes.append(f"Ability: {hero_name}'s Vanguard training improved frontline pressure.")

            elif name == "warden":
                injury_multiplier *= 0.85
                notes.append(f"Ability: {hero_name}'s Warden training reduced injury risk.")

            elif name == "captain" and len(heroes) >= 2:
                success_bonus += 0.03
                notes.append(f"Ability: {hero_name}'s Captain training improved team coordination.")

            elif name == "scout" and _task_values_stat(task, "swift", 4):
                success_bonus += 0.04
                notes.append(f"Ability: {hero_name}'s Scout training improved field approach.")

            elif name == "fixer" and (
                _task_values_stat(task, "wit", 4) or _task_values_stat(task, "presence", 4)
            ):
                success_bonus += 0.04
                notes.append(f"Ability: {hero_name}'s Fixer training helped solve mission complications.")

            elif name == "shadow" and _task_has_maximum_rules(task):
                success_bonus += 0.05
                notes.append(f"Ability: {hero_name}'s Shadow training handled delicate mission constraints.")

            elif name == "templar" and (
                _task_values_stat(task, "guard", 4) or "shrine" in str(getattr(task, "task_type", "")).lower()
            ):
                success_bonus += 0.04
                notes.append(f"Ability: {hero_name}'s Templar training steadied the mission.")

            elif name == "shepherd":
                satisfaction_bonus += 1
                notes.append(f"Ability: {hero_name}'s Shepherd training improved morale.")

            elif name == "oracle" and float(getattr(task, "decision_chance", 0.0)) > 0.0:
                success_bonus += 0.04
                notes.append(f"Ability: {hero_name}'s Oracle training anticipated the mission twist.")

            elif name == "arcanist" and _task_values_stat(task, "wit", 5):
                success_bonus += 0.05
                notes.append(f"Ability: {hero_name}'s Arcanist training strengthened magical problem solving.")

            elif name == "seer":
                success_bonus += 0.02
                notes.append(f"Ability: {hero_name}'s Seer training improved mission foresight.")

            elif name == "spellblade" and _task_is_mixed_might_wit(task):
                success_bonus += 0.05
                notes.append(f"Ability: {hero_name}'s Spellblade training excelled in a hybrid challenge.")

    unique_notes: List[str] = []
    seen = set()
    for line in notes:
        if line not in seen:
            seen.add(line)
            unique_notes.append(line)

    success_bonus = min(MAX_TOTAL_SUCCESS_BONUS, success_bonus)
    satisfaction_bonus = min(MAX_TOTAL_SATISFACTION_BONUS, satisfaction_bonus)
    injury_multiplier = max(MIN_INJURY_MULTIPLIER, injury_multiplier)

    return {
        "success_bonus": success_bonus,
        "injury_multiplier": injury_multiplier,
        "satisfaction_bonus": satisfaction_bonus,
        "notes": unique_notes[:6],
    }