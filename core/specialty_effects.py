import random
from typing import Dict, List

from .ui import highlight, success


def count_specialty(party, specialty: str) -> int:
    return sum(1 for hero in party if getattr(hero, "specialty", "") == specialty)


def has_specialty(party, specialty: str) -> bool:
    return count_specialty(party, specialty) > 0


def specialty_counts(party) -> Dict[str, int]:
    counts: Dict[str, int] = {}

    for hero in party:
        specialty = getattr(hero, "specialty", "")
        if not specialty:
            continue
        counts[specialty] = counts.get(specialty, 0) + 1

    return counts


def specialty_combat_power_bonus(hero, room_type: str) -> int:
    specialty = getattr(hero, "specialty", "")
    base_power = int(hero.combat_power())

    if specialty == "Boss Killer" and room_type == "Boss":
        return max(5, int(base_power * 0.25))

    if specialty == "Evoker" and room_type == "Monster":
        return max(4, int(base_power * 0.20))

    if specialty == "Weapon Master":
        return max(2, int(base_power * 0.08))

    return 0


def effective_party_power_for_room(party, room_type: str) -> int:
    total = 0

    for hero in party:
        total += int(hero.combat_power())
        total += specialty_combat_power_bonus(hero, room_type)

    return max(1, total)


def treasure_gold_multiplier(party) -> float:
    counts = specialty_counts(party)
    treasure_hunters = counts.get("Treasure Hunter", 0)
    return 1.0 + (0.20 * treasure_hunters)


def xp_multiplier(party) -> float:
    counts = specialty_counts(party)
    scholars = counts.get("Scholar", 0)
    return 1.0 + (0.15 * scholars)


def item_drop_bonus(party) -> float:
    counts = specialty_counts(party)
    seers = counts.get("Seer", 0)
    return 0.15 * seers


def wound_chance_multiplier(party) -> float:
    counts = specialty_counts(party)
    war_clerics = counts.get("War Cleric", 0)
    return max(0.55, 1.0 - (0.20 * war_clerics))


def first_room_damage_multiplier(party, room_number: int) -> float:
    if room_number != 1:
        return 1.0

    counts = specialty_counts(party)
    vanguards = counts.get("Vanguard", 0)
    return max(0.60, 1.0 - (0.15 * vanguards))


def apply_life_cleric_healing(party) -> List[str]:
    messages: List[str] = []
    counts = specialty_counts(party)
    life_clerics = counts.get("Life Cleric", 0)

    if life_clerics <= 0:
        return messages

    heal_amount = 6 * life_clerics
    messages.append(success(f"Life Cleric passive restores {heal_amount} HP to the party."))

    for hero in party:
        current_health = getattr(hero, "current_health", None)
        if current_health is not None and current_health > 0:
            messages.append(success(hero.heal(heal_amount)))

    return messages


def try_grave_cleric_save(party, dying_hero) -> List[str]:
    messages: List[str] = []

    grave_clerics = [
        hero
        for hero in party
        if hero is not dying_hero
        and getattr(hero, "specialty", "") == "Grave Cleric"
        and int(getattr(hero, "current_health", 0) or 0) > 0
    ]

    if not grave_clerics:
        return messages

    save_chance = min(0.80, 0.35 * len(grave_clerics))

    if random.random() <= save_chance:
        dying_hero.current_health = max(1, int(dying_hero.max_health() * 0.15))
        messages.append(
            highlight(
                f"Grave Cleric intervention saves {dying_hero.name} from death "
                f"({dying_hero.current_health}/{dying_hero.max_health()} HP)."
            )
        )

    return messages