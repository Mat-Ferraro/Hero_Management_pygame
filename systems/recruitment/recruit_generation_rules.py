from __future__ import annotations

import random
from typing import Dict, Tuple

from systems.progression.hero_career import CAREER_PHASES_BY_CLASS


DEFAULT_RECRUIT_PHASE_WEIGHTS: Dict[str, int] = {
    "Rookie": 42,
    "Rising": 28,
    "Prime": 18,
    "Veteran": 9,
    "Elder": 3,
}

DEFAULT_DEVELOPMENTAL_PHASE_WEIGHTS: Dict[str, int] = {
    "Rookie": 85,
    "Rising": 15,
}


RECRUIT_PHASE_WEIGHTS_BY_CLASS: Dict[str, Dict[str, int]] = {
    "Rogue": {
        "Rookie": 46,
        "Rising": 30,
        "Prime": 16,
        "Veteran": 6,
        "Elder": 2,
    },
    "Warrior": {
        "Rookie": 42,
        "Rising": 30,
        "Prime": 18,
        "Veteran": 8,
        "Elder": 2,
    },
    "Cleric": {
        "Rookie": 40,
        "Rising": 28,
        "Prime": 20,
        "Veteran": 9,
        "Elder": 3,
    },
    "Mage": {
        "Rookie": 38,
        "Rising": 28,
        "Prime": 21,
        "Veteran": 10,
        "Elder": 3,
    },
}

DEVELOPMENTAL_PHASE_WEIGHTS_BY_CLASS: Dict[str, Dict[str, int]] = {
    "Rogue": {"Rookie": 80, "Rising": 20},
    "Warrior": {"Rookie": 82, "Rising": 18},
    "Cleric": {"Rookie": 86, "Rising": 14},
    "Mage": {"Rookie": 90, "Rising": 10},
}


LEVEL_RANGES_BY_CLASS: Dict[str, Dict[str, Tuple[int, int]]] = {
    "Rogue": {
        "Rookie": (1, 2),
        "Rising": (2, 4),
        "Prime": (4, 6),
        "Veteran": (4, 6),
        "Elder": (3, 5),
    },
    "Warrior": {
        "Rookie": (1, 2),
        "Rising": (2, 4),
        "Prime": (4, 6),
        "Veteran": (4, 6),
        "Elder": (3, 5),
    },
    "Cleric": {
        "Rookie": (1, 2),
        "Rising": (2, 4),
        "Prime": (4, 6),
        "Veteran": (4, 7),
        "Elder": (4, 7),
    },
    "Mage": {
        "Rookie": (1, 2),
        "Rising": (2, 4),
        "Prime": (4, 7),
        "Veteran": (4, 7),
        "Elder": (4, 7),
    },
}

DEFAULT_LEVEL_RANGES: Dict[str, Tuple[int, int]] = {
    "Rookie": (1, 2),
    "Rising": (2, 4),
    "Prime": (4, 6),
    "Veteran": (4, 6),
    "Elder": (3, 5),
}


def weighted_choice(weight_map: Dict[str, int]) -> str:
    if not weight_map:
        return "Rookie"

    cleaned_weights = {
        str(key): max(0, int(value))
        for key, value in weight_map.items()
    }

    total = sum(cleaned_weights.values())
    if total <= 0:
        return next(iter(cleaned_weights))

    roll = random.randint(1, total)
    running_total = 0

    for value, weight in cleaned_weights.items():
        running_total += weight
        if roll <= running_total:
            return value

    return next(iter(cleaned_weights))


def phase_age_range_for_class(class_name: str, phase_name: str) -> tuple[int, int]:
    phase_table = CAREER_PHASES_BY_CLASS.get(class_name, [])

    for name, min_age, max_age in phase_table:
        if name != phase_name:
            continue

        low = int(min_age)
        high = int(max_age) if max_age is not None else (low + 8)
        return low, max(low, high)

    return 18, 24


def recruit_phase_weights_for_class(class_name: str) -> Dict[str, int]:
    return dict(RECRUIT_PHASE_WEIGHTS_BY_CLASS.get(class_name, DEFAULT_RECRUIT_PHASE_WEIGHTS))


def developmental_phase_weights_for_class(class_name: str) -> Dict[str, int]:
    return dict(DEVELOPMENTAL_PHASE_WEIGHTS_BY_CLASS.get(class_name, DEFAULT_DEVELOPMENTAL_PHASE_WEIGHTS))


def choose_phase_for_new_recruit(class_name: str, developmental: bool = False) -> str:
    if developmental:
        return weighted_choice(developmental_phase_weights_for_class(class_name))

    return weighted_choice(recruit_phase_weights_for_class(class_name))


def choose_age_for_phase(class_name: str, phase_name: str) -> int:
    low, high = phase_age_range_for_class(class_name, phase_name)
    return random.randint(low, high)


def level_range_for_phase(class_name: str, phase_name: str) -> tuple[int, int]:
    class_ranges = LEVEL_RANGES_BY_CLASS.get(class_name, DEFAULT_LEVEL_RANGES)
    low, high = class_ranges.get(phase_name, DEFAULT_LEVEL_RANGES["Rookie"])
    return int(low), int(high)


def choose_level_for_phase(state, class_name: str, phase_name: str) -> int:
    level_cap = int(getattr(state.guild_upgrades, "recruit_level_cap", 1))

    low, high = level_range_for_phase(class_name, phase_name)
    high = min(high, level_cap)
    low = min(low, high)

    if high < 1:
        return 1

    return random.randint(max(1, low), max(1, high))