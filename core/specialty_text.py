import random
from typing import Dict, List

from .ui import info


SPECIALTIES_BY_CLASS: Dict[str, List[str]] = {
    "Warrior": ["Guardian", "Weapon Master", "Vanguard"],
    "Rogue": ["Treasure Hunter", "Scout", "Boss Killer"],
    "Cleric": ["Life Cleric", "Grave Cleric", "War Cleric"],
    "Mage": ["Seer", "Evoker", "Scholar"],
}


SPECIALTY_DESCRIPTIONS: Dict[str, str] = {
    "Guardian": "May prevent lethal damage to an ally.",
    "Weapon Master": "Currently grants a small combat bonus.",
    "Vanguard": "Reduces party damage in the first room.",
    "Treasure Hunter": "Increases gold found in treasure rooms.",
    "Scout": "Currently informational flavor and future scouting support.",
    "Boss Killer": "Gains extra combat power in boss rooms.",
    "Life Cleric": "Heals the party after each room.",
    "Grave Cleric": "May prevent a hero death once per expedition.",
    "War Cleric": "Reduces chance of wounds after combat.",
    "Seer": "Improves item discovery chance.",
    "Evoker": "Gains extra combat power in monster rooms.",
    "Scholar": "Increases combat XP earned by the party.",
}


def random_specialty_for_class(hero_class: str) -> str:
    options = SPECIALTIES_BY_CLASS.get(hero_class, [])
    if not options:
        return "Adventurer"
    return random.choice(options)


def specialty_description(specialty: str) -> str:
    return SPECIALTY_DESCRIPTIONS.get(specialty, "No specialty description yet.")


def describe_party_specialties(party) -> List[str]:
    active = []

    for hero in party:
        specialty = getattr(hero, "specialty", "")
        if specialty:
            active.append(f"{hero.name}: {specialty}")

    if not active:
        return []

    return [info("Active party specialties: " + "; ".join(active))]