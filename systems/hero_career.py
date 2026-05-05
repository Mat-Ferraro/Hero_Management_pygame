from __future__ import annotations

from typing import Dict, List, Tuple


STAT_NAMES = ["might", "agility", "mind", "spirit"]

CAREER_PHASES_BY_CLASS: Dict[str, List[Tuple[str, int, int | None]]] = {
    "Rogue": [
        ("Rookie", 18, 22),
        ("Rising", 23, 27),
        ("Prime", 28, 32),
        ("Veteran", 33, 37),
        ("Elder", 38, None),
    ],
    "Warrior": [
        ("Rookie", 18, 23),
        ("Rising", 24, 29),
        ("Prime", 30, 36),
        ("Veteran", 37, 43),
        ("Elder", 44, None),
    ],
    "Cleric": [
        ("Rookie", 18, 24),
        ("Rising", 25, 31),
        ("Prime", 32, 40),
        ("Veteran", 41, 49),
        ("Elder", 50, None),
    ],
    "Mage": [
        ("Rookie", 18, 26),
        ("Rising", 27, 35),
        ("Prime", 36, 48),
        ("Veteran", 49, 58),
        ("Elder", 59, None),
    ],
}

DEFAULT_PHASES: List[Tuple[str, int, int | None]] = [
    ("Rookie", 18, 24),
    ("Rising", 25, 31),
    ("Prime", 32, 40),
    ("Veteran", 41, 49),
    ("Elder", 50, None),
]

PHASE_STAT_MODIFIERS: Dict[str, Dict[str, Dict[str, int]]] = {
    "Rogue": {
        "Rookie": {"might": -1, "agility": 1, "mind": 0, "spirit": 0},
        "Rising": {"might": 0, "agility": 2, "mind": 1, "spirit": 0},
        "Prime": {"might": 1, "agility": 3, "mind": 1, "spirit": 0},
        "Veteran": {"might": 0, "agility": 1, "mind": 2, "spirit": 1},
        "Elder": {"might": -1, "agility": -1, "mind": 2, "spirit": 1},
    },
    "Warrior": {
        "Rookie": {"might": 0, "agility": 0, "mind": -1, "spirit": 0},
        "Rising": {"might": 2, "agility": 1, "mind": 0, "spirit": 0},
        "Prime": {"might": 3, "agility": 1, "mind": 0, "spirit": 1},
        "Veteran": {"might": 1, "agility": 0, "mind": 1, "spirit": 1},
        "Elder": {"might": -1, "agility": -1, "mind": 1, "spirit": 1},
    },
    "Cleric": {
        "Rookie": {"might": 0, "agility": 0, "mind": 0, "spirit": 1},
        "Rising": {"might": 0, "agility": 0, "mind": 1, "spirit": 2},
        "Prime": {"might": 1, "agility": 0, "mind": 2, "spirit": 3},
        "Veteran": {"might": 0, "agility": -1, "mind": 2, "spirit": 2},
        "Elder": {"might": -1, "agility": -1, "mind": 1, "spirit": 2},
    },
    "Mage": {
        "Rookie": {"might": -1, "agility": 0, "mind": 1, "spirit": 0},
        "Rising": {"might": -1, "agility": 0, "mind": 2, "spirit": 1},
        "Prime": {"might": 0, "agility": 0, "mind": 4, "spirit": 2},
        "Veteran": {"might": 0, "agility": -1, "mind": 3, "spirit": 2},
        "Elder": {"might": -1, "agility": -1, "mind": 2, "spirit": 2},
    },
}

DEFAULT_PHASE_MODIFIERS: Dict[str, Dict[str, int]] = {
    "Rookie": {"might": 0, "agility": 0, "mind": 0, "spirit": 0},
    "Rising": {"might": 1, "agility": 0, "mind": 1, "spirit": 0},
    "Prime": {"might": 1, "agility": 1, "mind": 1, "spirit": 1},
    "Veteran": {"might": 0, "agility": 0, "mind": 1, "spirit": 1},
    "Elder": {"might": -1, "agility": -1, "mind": 1, "spirit": 1},
}


def career_phases_for_class(hero_class: str) -> List[Tuple[str, int, int | None]]:
    return list(CAREER_PHASES_BY_CLASS.get(str(hero_class), DEFAULT_PHASES))


def career_phase_name(hero) -> str:
    hero_class = str(getattr(hero, "hero_class", ""))
    age = int(getattr(hero, "age", 18))

    for phase_name, min_age, max_age in career_phases_for_class(hero_class):
        if age < min_age:
            continue
        if max_age is None or age <= max_age:
            return phase_name

    return "Prime"


def phase_modifiers_for_hero(hero) -> Dict[str, int]:
    hero_class = str(getattr(hero, "hero_class", ""))
    phase_name = career_phase_name(hero)

    class_table = PHASE_STAT_MODIFIERS.get(hero_class, {})
    modifiers = dict(class_table.get(phase_name, DEFAULT_PHASE_MODIFIERS.get(phase_name, {})))

    return {
        stat_name: int(modifiers.get(stat_name, 0))
        for stat_name in STAT_NAMES
    }


def effective_stat(hero, stat_name: str) -> int:
    stat_name = str(stat_name)

    base_value = 0
    try:
        base_value = int(hero.total_stat(stat_name))
    except Exception:
        base_value = int(getattr(hero, "stats", {}).get(stat_name, 0))

    modifiers = phase_modifiers_for_hero(hero)
    return max(0, base_value + int(modifiers.get(stat_name, 0)))


def effective_stats_snapshot(hero) -> Dict[str, int]:
    return {
        stat_name: effective_stat(hero, stat_name)
        for stat_name in STAT_NAMES
    }


def career_phase_summary(hero) -> str:
    phase_name = career_phase_name(hero)
    modifiers = phase_modifiers_for_hero(hero)

    pieces = []
    for stat_name in STAT_NAMES:
        value = int(modifiers.get(stat_name, 0))
        if value == 0:
            continue
        sign = "+" if value > 0 else ""
        pieces.append(f"{stat_name} {sign}{value}")

    if not pieces:
        return phase_name

    return f"{phase_name} ({', '.join(pieces)})"