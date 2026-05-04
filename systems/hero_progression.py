from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, Tuple


SUBCLASS_UNLOCK_THRESHOLD = 3

CLASS_TRAINING_PATHS: Dict[str, Dict[str, Dict]] = {
    "Warrior": {
        "Vanguard": {
            "subclass_name": "Vanguard",
            "ability_name": "Forward Pressure",
            "ranks": [
                {"stats": {"might": 1}},
                {"stats": {"might": 1, "agility": 1}},
                {"stats": {"might": 2}},
            ],
        },
        "Warden": {
            "subclass_name": "Warden",
            "ability_name": "Bulwark",
            "ranks": [
                {"stats": {"might": 1, "spirit": 1}},
                {"stats": {"spirit": 2}},
                {"stats": {"might": 1, "spirit": 2}},
            ],
        },
        "Captain": {
            "subclass_name": "Captain",
            "ability_name": "Rallying Command",
            "ranks": [
                {"stats": {"spirit": 1}},
                {"stats": {"might": 1, "spirit": 1}},
                {"stats": {"spirit": 2}},
            ],
        },
    },
    "Rogue": {
        "Scout": {
            "subclass_name": "Scout",
            "ability_name": "Quick Approach",
            "ranks": [
                {"stats": {"agility": 1}},
                {"stats": {"agility": 1, "mind": 1}},
                {"stats": {"agility": 2}},
            ],
        },
        "Fixer": {
            "subclass_name": "Fixer",
            "ability_name": "Underworld Touch",
            "ranks": [
                {"stats": {"mind": 1}},
                {"stats": {"mind": 1, "spirit": 1}},
                {"stats": {"mind": 2}},
            ],
        },
        "Shadow": {
            "subclass_name": "Shadow",
            "ability_name": "Silent Work",
            "ranks": [
                {"stats": {"agility": 1}},
                {"stats": {"agility": 1, "mind": 1}},
                {"stats": {"agility": 1, "mind": 1}},
            ],
        },
    },
    "Cleric": {
        "Templar": {
            "subclass_name": "Templar",
            "ability_name": "Sanctified Guard",
            "ranks": [
                {"stats": {"might": 1, "spirit": 1}},
                {"stats": {"spirit": 1}},
                {"stats": {"might": 1, "spirit": 2}},
            ],
        },
        "Shepherd": {
            "subclass_name": "Shepherd",
            "ability_name": "Guiding Presence",
            "ranks": [
                {"stats": {"spirit": 1}},
                {"stats": {"mind": 1, "spirit": 1}},
                {"stats": {"spirit": 2}},
            ],
        },
        "Oracle": {
            "subclass_name": "Oracle",
            "ability_name": "Divine Insight",
            "ranks": [
                {"stats": {"mind": 1}},
                {"stats": {"mind": 1, "spirit": 1}},
                {"stats": {"mind": 2}},
            ],
        },
    },
    "Mage": {
        "Arcanist": {
            "subclass_name": "Arcanist",
            "ability_name": "Arcane Surge",
            "ranks": [
                {"stats": {"mind": 1}},
                {"stats": {"mind": 2}},
                {"stats": {"mind": 2}},
            ],
        },
        "Seer": {
            "subclass_name": "Seer",
            "ability_name": "Foresight",
            "ranks": [
                {"stats": {"mind": 1}},
                {"stats": {"mind": 1, "agility": 1}},
                {"stats": {"mind": 1, "spirit": 1}},
            ],
        },
        "Spellblade": {
            "subclass_name": "Spellblade",
            "ability_name": "Arcsteel Form",
            "ranks": [
                {"stats": {"might": 1, "mind": 1}},
                {"stats": {"might": 1}},
                {"stats": {"might": 1, "mind": 1}},
            ],
        },
    },
}


def ensure_progression_fields(hero) -> None:
    if not hasattr(hero, "training_points"):
        hero.training_points = 0

    if not hasattr(hero, "training_path_progress") or hero.training_path_progress is None:
        hero.training_path_progress = {}

    if not hasattr(hero, "unlocked_subclasses") or hero.unlocked_subclasses is None:
        hero.unlocked_subclasses = []

    if not hasattr(hero, "unlocked_abilities") or hero.unlocked_abilities is None:
        hero.unlocked_abilities = []

    if not hasattr(hero, "primary_subclass") or hero.primary_subclass is None:
        hero.primary_subclass = None

    if not hasattr(hero, "subclass"):
        hero.subclass = None

    if not hasattr(hero, "special_ability"):
        hero.special_ability = None


def progression_to_dict(hero) -> Dict:
    ensure_progression_fields(hero)
    return {
        "training_points": int(getattr(hero, "training_points", 0)),
        "training_path_progress": dict(getattr(hero, "training_path_progress", {})),
        "unlocked_subclasses": list(getattr(hero, "unlocked_subclasses", [])),
        "unlocked_abilities": list(getattr(hero, "unlocked_abilities", [])),
        "primary_subclass": getattr(hero, "primary_subclass", None),
    }


def apply_progression_from_dict(hero, data: Dict | None) -> None:
    ensure_progression_fields(hero)
    data = data or {}

    hero.training_points = int(data.get("training_points", 0))
    hero.training_path_progress = {
        str(path_name): int(rank)
        for path_name, rank in data.get("training_path_progress", {}).items()
    }
    hero.unlocked_subclasses = list(data.get("unlocked_subclasses", []))
    hero.unlocked_abilities = list(data.get("unlocked_abilities", []))
    hero.primary_subclass = data.get("primary_subclass")

    if hero.primary_subclass and not hero.subclass:
        hero.subclass = hero.primary_subclass

    if hero.unlocked_abilities and not hero.special_ability:
        hero.special_ability = hero.unlocked_abilities[0]


def available_training_paths(hero) -> Dict[str, Dict]:
    ensure_progression_fields(hero)
    return deepcopy(CLASS_TRAINING_PATHS.get(getattr(hero, "hero_class", ""), {}))


def training_rank_for_path(hero, path_name: str) -> int:
    ensure_progression_fields(hero)
    return int(hero.training_path_progress.get(path_name, 0))


def can_spend_training_point(hero, path_name: str) -> Tuple[bool, str]:
    ensure_progression_fields(hero)

    if getattr(hero, "is_temporary_survivor", False):
        return False, "Temporary survivors cannot specialize."

    if getattr(hero, "injured_years_remaining", 0) > 0:
        return False, "Injured heroes cannot specialize."

    if int(getattr(hero, "training_points", 0)) <= 0:
        return False, "No training points available."

    paths = available_training_paths(hero)
    if path_name not in paths:
        return False, f"{path_name} is not valid for {hero.hero_class}."

    current_rank = training_rank_for_path(hero, path_name)
    rank_rewards = paths[path_name]["ranks"]
    if current_rank >= len(rank_rewards):
        return False, f"{path_name} is already mastered."

    return True, ""


def _add_unique_string(target_list: List[str], value: str) -> bool:
    if value not in target_list:
        target_list.append(value)
        return True
    return False


def spend_training_point(hero, path_name: str) -> List[str]:
    ensure_progression_fields(hero)

    allowed, reason = can_spend_training_point(hero, path_name)
    if not allowed:
        return [reason]

    paths = available_training_paths(hero)
    path_data = paths[path_name]

    current_rank = training_rank_for_path(hero, path_name)
    reward_data = path_data["ranks"][current_rank]
    stat_gains = dict(reward_data.get("stats", {}))

    hero.training_points -= 1
    hero.training_path_progress[path_name] = current_rank + 1

    messages = [f"{hero.name} trained in {path_name}."]
    for stat_name, amount in stat_gains.items():
        hero.stats[stat_name] = int(hero.stats.get(stat_name, 0)) + int(amount)
        messages.append(f"  +{int(amount)} {stat_name}")

    if hero.training_path_progress[path_name] >= SUBCLASS_UNLOCK_THRESHOLD:
        subclass_name = str(path_data.get("subclass_name", path_name))
        ability_name = str(path_data.get("ability_name", ""))

        if _add_unique_string(hero.unlocked_subclasses, subclass_name):
            messages.append(f"{hero.name} unlocked subclass: {subclass_name}.")

        if ability_name and _add_unique_string(hero.unlocked_abilities, ability_name):
            messages.append(f"{hero.name} learned ability: {ability_name}.")

        if not getattr(hero, "primary_subclass", None):
            hero.primary_subclass = subclass_name
            messages.append(f"{hero.name}'s primary subclass is now {subclass_name}.")

        if not getattr(hero, "subclass", None):
            hero.subclass = subclass_name

        if not getattr(hero, "special_ability", None) and hero.unlocked_abilities:
            hero.special_ability = hero.unlocked_abilities[0]

    return messages


def award_training_points(hero, amount: int) -> List[str]:
    ensure_progression_fields(hero)
    amount = max(0, int(amount))
    if amount <= 0:
        return []

    hero.training_points += amount
    return [f"{hero.name} gained {amount} training point(s)."]


def award_training_points_for_outcome(hero, outcome_band: str) -> List[str]:
    mapping = {
        "great_success": 2,
        "success": 1,
        "partial_success": 1,
        "critical_failure": 0,
    }
    return award_training_points(hero, mapping.get(str(outcome_band), 0))