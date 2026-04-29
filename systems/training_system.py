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
    return TRAINING_COST_BY_LEVEL.get(training_hall_level, TRAINING_COST_BY_LEVEL[1])


def training_xp(training_hall_level: int) -> int:
    return TRAINING_XP_BY_LEVEL.get(training_hall_level, TRAINING_XP_BY_LEVEL[1])


def can_train_hero(hero) -> tuple[bool, str]:
    if hero.is_temporary_survivor:
        return False, "Temporary survivors cannot train."

    if hero.injured_years_remaining > 0:
        return False, "Injured heroes cannot train."

    return True, ""


def train_hero(state, hero) -> list[str]:
    messages = []

    level = state.guild_upgrades.training_hall_level
    if level <= 0:
        return ["Training Hall is locked."]

    if hero not in state.roster:
        return ["That hero is not in your roster."]

    allowed, reason = can_train_hero(hero)
    if not allowed:
        return [reason]

    cost = training_cost(level)
    xp = training_xp(level)

    if state.gold < cost:
        return [f"Not enough gold. Training costs {cost}g."]

    state.gold -= cost

    messages.append(f"Paid {cost}g to train {hero.name}.")
    messages.extend(hero.add_xp(xp))

    hero.adjust_satisfaction(2, "received training")
    messages.append(f"{hero.name} appreciated the training opportunity.")

    return messages