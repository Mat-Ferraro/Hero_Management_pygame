from dataclasses import dataclass, field
from typing import Dict, List


CLASS_UNLOCK_ORDER = ["Warrior", "Rogue", "Cleric", "Mage"]


@dataclass
class GuildUpgrades:
    roster_capacity: int = 1
    unlocked_classes: List[str] = field(default_factory=lambda: ["Warrior"])
    recruit_level_cap: int = 1
    market_unlocked: bool = False
    market_rarity_cap: str = "Common"
    mission_difficulty_cap: int = 1
    crown_stipend: int = 50
    training_hall_level: int = 0


UPGRADE_DEFINITIONS: Dict[str, Dict] = {
    "roster_capacity_2": {
        "name": "Expand Lodging I",
        "cost": 150,
        "description": "Increase guild roster capacity to 2 heroes.",
        "requires": lambda upgrades: upgrades.roster_capacity < 2,
        "apply": lambda upgrades: setattr(upgrades, "roster_capacity", 2),
    },
    "roster_capacity_4": {
        "name": "Expand Lodging II",
        "cost": 300,
        "description": "Increase guild roster capacity to 4 heroes.",
        "requires": lambda upgrades: upgrades.roster_capacity == 2,
        "apply": lambda upgrades: setattr(upgrades, "roster_capacity", 4),
    },
    "roster_capacity_6": {
        "name": "Expand Lodging III",
        "cost": 600,
        "description": "Increase guild roster capacity to 6 heroes.",
        "requires": lambda upgrades: upgrades.roster_capacity == 4,
        "apply": lambda upgrades: setattr(upgrades, "roster_capacity", 6),
    },
    "unlock_training_hall": {
        "name": "Build Training Hall",
        "cost": 175,
        "description": "Unlock paid hero training during the guild phase.",
        "requires": lambda upgrades: upgrades.training_hall_level < 1,
        "apply": lambda upgrades: setattr(upgrades, "training_hall_level", 1),
    },
    "training_hall_2": {
        "name": "Improve Training Hall I",
        "cost": 350,
        "description": "Improve training XP gains.",
        "requires": lambda upgrades: upgrades.training_hall_level == 1,
        "apply": lambda upgrades: setattr(upgrades, "training_hall_level", 2),
    },
    "training_hall_3": {
        "name": "Improve Training Hall II",
        "cost": 700,
        "description": "Further improve training XP gains. Future: unlock specialization.",
        "requires": lambda upgrades: upgrades.training_hall_level == 2,
        "apply": lambda upgrades: setattr(upgrades, "training_hall_level", 3),
    },
    "unlock_rogue": {
        "name": "Build Rogue Den",
        "cost": 200,
        "description": "Rogues can appear as recruits.",
        "requires": lambda upgrades: "Rogue" not in upgrades.unlocked_classes,
        "apply": lambda upgrades: upgrades.unlocked_classes.append("Rogue"),
    },
    "unlock_cleric": {
        "name": "Build Shrine",
        "cost": 275,
        "description": "Clerics can appear as recruits.",
        "requires": lambda upgrades: "Cleric" not in upgrades.unlocked_classes,
        "apply": lambda upgrades: upgrades.unlocked_classes.append("Cleric"),
    },
    "unlock_mage": {
        "name": "Build Arcane Study",
        "cost": 400,
        "description": "Mages can appear as recruits.",
        "requires": lambda upgrades: "Mage" not in upgrades.unlocked_classes,
        "apply": lambda upgrades: upgrades.unlocked_classes.append("Mage"),
    },
    "recruit_level_3": {
        "name": "Improve Recruitment I",
        "cost": 250,
        "description": "Recruits may appear up to level 3.",
        "requires": lambda upgrades: upgrades.recruit_level_cap < 3,
        "apply": lambda upgrades: setattr(upgrades, "recruit_level_cap", 3),
    },
    "recruit_level_5": {
        "name": "Improve Recruitment II",
        "cost": 500,
        "description": "Recruits may appear up to level 5.",
        "requires": lambda upgrades: upgrades.recruit_level_cap == 3,
        "apply": lambda upgrades: setattr(upgrades, "recruit_level_cap", 5),
    },
    "unlock_market": {
        "name": "Open Guild Market",
        "cost": 200,
        "description": "Unlock the market screen.",
        "requires": lambda upgrades: not upgrades.market_unlocked,
        "apply": lambda upgrades: setattr(upgrades, "market_unlocked", True),
    },
    "stipend_100": {
        "name": "Petition the Crown I",
        "cost": 250,
        "description": "Increase crown stipend to 100g per campaign.",
        "requires": lambda upgrades: upgrades.crown_stipend < 100,
        "apply": lambda upgrades: setattr(upgrades, "crown_stipend", 100),
    },
    "mission_diff_2": {
        "name": "Scout Dangerous Roads I",
        "cost": 225,
        "description": "Unlock difficulty 2 missions.",
        "requires": lambda upgrades: upgrades.mission_difficulty_cap < 2,
        "apply": lambda upgrades: setattr(upgrades, "mission_difficulty_cap", 2),
    },
    "mission_diff_3": {
        "name": "Scout Dangerous Roads II",
        "cost": 450,
        "description": "Unlock difficulty 3 missions.",
        "requires": lambda upgrades: upgrades.mission_difficulty_cap == 2,
        "apply": lambda upgrades: setattr(upgrades, "mission_difficulty_cap", 3),
    },
}


def available_upgrades(upgrades: GuildUpgrades):
    return [
        (upgrade_id, definition)
        for upgrade_id, definition in UPGRADE_DEFINITIONS.items()
        if definition["requires"](upgrades)
    ]


def buy_upgrade(state, upgrade_id: str) -> str:
    if upgrade_id not in UPGRADE_DEFINITIONS:
        return "Unknown upgrade."

    definition = UPGRADE_DEFINITIONS[upgrade_id]
    upgrades = state.guild_upgrades

    if not definition["requires"](upgrades):
        return "That upgrade is not currently available."

    cost = definition["cost"]
    if state.gold < cost:
        return f"Not enough gold. {definition['name']} costs {cost}g."

    state.gold -= cost
    definition["apply"](upgrades)

    return f"Purchased upgrade: {definition['name']}."


def guild_upgrades_to_dict(upgrades: GuildUpgrades) -> Dict:
    return {
        "roster_capacity": upgrades.roster_capacity,
        "unlocked_classes": list(upgrades.unlocked_classes),
        "recruit_level_cap": upgrades.recruit_level_cap,
        "market_unlocked": upgrades.market_unlocked,
        "market_rarity_cap": upgrades.market_rarity_cap,
        "mission_difficulty_cap": upgrades.mission_difficulty_cap,
        "crown_stipend": upgrades.crown_stipend,
        "training_hall_level": upgrades.training_hall_level,
    }


def guild_upgrades_from_dict(data: Dict | None) -> GuildUpgrades:
    if not data:
        return GuildUpgrades()

    roster_capacity = data.get("roster_capacity", data.get("party_slots", 1))

    return GuildUpgrades(
        roster_capacity=int(roster_capacity),
        unlocked_classes=list(data.get("unlocked_classes", ["Warrior"])),
        recruit_level_cap=int(data.get("recruit_level_cap", 1)),
        market_unlocked=bool(data.get("market_unlocked", False)),
        market_rarity_cap=data.get("market_rarity_cap", "Common"),
        mission_difficulty_cap=int(data.get("mission_difficulty_cap", 1)),
        crown_stipend=int(data.get("crown_stipend", 50)),
        training_hall_level=int(data.get("training_hall_level", 0)),
    )