from __future__ import annotations

from systems.progression.hero_progression import (
    available_training_paths,
    can_spend_training_point,
    ensure_progression_fields,
    spend_training_point,
)

TRAINING_COST_BY_LEVEL = {
    1: 50,
    2: 75,
    3: 100,
}

TRAINING_XP_BY_LEVEL = {
    1: 60,
    2: 95,
    3: 140,
}


def training_cost(training_hall_level: int) -> int:
    return int(TRAINING_COST_BY_LEVEL.get(int(training_hall_level), TRAINING_COST_BY_LEVEL[1]))


def training_xp(training_hall_level: int) -> int:
    return int(TRAINING_XP_BY_LEVEL.get(int(training_hall_level), TRAINING_XP_BY_LEVEL[1]))


def can_train_hero(hero) -> tuple[bool, str]:
    ensure_progression_fields(hero)

    if getattr(hero, "is_temporary_survivor", False):
        return False, "Temporary survivors cannot train."

    if int(getattr(hero, "injured_years_remaining", 0)) > 0:
        return False, "Injured heroes cannot train."

    return True, ""


def train_hero(state, hero) -> list[str]:
    level = int(getattr(state.guild_upgrades, "training_hall_level", 0))
    if level <= 0:
        return ["Training Hall is locked."]

    if hero not in getattr(state, "roster", []):
        return ["That hero is not in your roster."]

    allowed, reason = can_train_hero(hero)
    if not allowed:
        return [reason]

    cost = training_cost(level)
    xp = training_xp(level)

    if int(getattr(state, "gold", 0)) < cost:
        return [f"Not enough gold. Training costs {cost}g."]

    state.gold -= cost

    messages = [f"Paid {cost}g to train {hero.name}."]
    messages.extend(hero.add_xp(xp))
    messages.append(hero.adjust_satisfaction(2, "received training"))

    return messages


def specialization_paths_for_hero(hero) -> dict:
    ensure_progression_fields(hero)
    return available_training_paths(hero)


def can_specialize_hero(hero, path_name: str) -> tuple[bool, str]:
    ensure_progression_fields(hero)
    return can_spend_training_point(hero, path_name)


def specialize_hero(hero, path_name: str) -> list[str]:
    ensure_progression_fields(hero)
    return spend_training_point(hero, path_name)