"""
core/combat_types.py

Enemy type rules, damage type matchups, and combat multiplier calculations.

Equipment integration (cleanup):
  hero_matchup_multiplier() and incoming_damage_multiplier() previously used
  raw getattr loops over hero.equipment.values().  They now delegate to
  equipment_effects, which also picks up active synergy bonuses.

  item_matches_enemy_type() is updated to use equipment_effects.item_relevant_for_enemy()
  for consistency, while keeping the damage_type cross-check logic local since
  it requires enemy rule data.
"""

from typing import Any, Dict, List

from ui import info, success, warning


CLASS_DAMAGE_TYPES: Dict[str, str] = {
    "Warrior": "Physical",
    "Rogue":   "Physical",
    "Mage":    "Magic",
    "Cleric":  "Holy",
}

DEFAULT_ENEMY_RULES: Dict[str, Any] = {
    "weak_to":    [],
    "resists":    [],
    "description": "Unknown enemy type.",
}

ENEMY_TYPE_RULES: Dict[str, Dict[str, Any]] = {
    "Beasts": {
        "weak_to":     ["Physical"],
        "resists":     [],
        "description": "Living monsters. Vulnerable to direct physical force.",
    },
    "Bandits": {
        "weak_to":     ["Physical"],
        "resists":     ["Holy"],
        "description": "Human enemies. Vulnerable to martial pressure; less affected by holy rites.",
    },
    "Undead": {
        "weak_to":     ["Holy"],
        "resists":     ["Physical"],
        "description": "Dead things. Holy power is effective; physical attacks are less reliable.",
    },
    "Spirits": {
        "weak_to":     ["Magic", "Holy"],
        "resists":     ["Physical"],
        "description": "Incorporeal enemies. Physical attacks struggle; magic and holy power work well.",
    },
    "Demons": {
        "weak_to":     ["Holy"],
        "resists":     ["Magic"],
        "description": "Corrupt outsiders. Holy power is strong; raw magic is resisted.",
    },
    "Dragons": {
        "weak_to":     ["Magic"],
        "resists":     ["Physical"],
        "description": "Ancient monsters. Physical attacks struggle against scales; magic is effective.",
    },
}


# ---------------------------------------------------------------------------
# Basic lookups
# ---------------------------------------------------------------------------

def damage_type_for_hero(hero) -> str:
    return CLASS_DAMAGE_TYPES.get(getattr(hero, "hero_class", ""), "Physical")


def enemy_rules(enemy_type: str) -> Dict[str, Any]:
    rules = ENEMY_TYPE_RULES.get(enemy_type)
    return dict(rules) if rules is not None else dict(DEFAULT_ENEMY_RULES)


# ---------------------------------------------------------------------------
# Combat multipliers — now use equipment_effects
# ---------------------------------------------------------------------------

def hero_matchup_multiplier(hero, enemy_type: str) -> float:
    """
    Full outgoing damage multiplier for hero vs enemy_type.
    Accounts for damage type matchup AND all equipped item bonuses
    (including active synergy bonuses via equipment_effects).
    """
    damage_type = damage_type_for_hero(hero)
    rules       = enemy_rules(enemy_type)

    multiplier = 1.0

    if damage_type in rules.get("weak_to", []):
        multiplier *= 1.25
    if damage_type in rules.get("resists", []):
        multiplier *= 0.75

    try:
        from systems.equipment.equipment_effects import (
            hero_damage_type_multiplier,
            hero_enemy_type_multiplier,
        )
        multiplier *= hero_damage_type_multiplier(hero, damage_type)
        multiplier *= hero_enemy_type_multiplier(hero, enemy_type)
    except Exception:
        # Fallback: raw getattr loop if equipment_effects unavailable.
        for item in list(getattr(hero, "equipment", {}).values()):
            multiplier *= 1.0 + float(getattr(item, "damage_type_bonus", {}).get(damage_type, 0.0))
            multiplier *= 1.0 + float(getattr(item, "enemy_type_bonus", {}).get(enemy_type, 0.0))

    return multiplier


def incoming_damage_multiplier(hero, enemy_type: str) -> float:
    """
    Incoming damage multiplier from enemy_type after equipment resistance.
    Clamped to a minimum of 0.35.
    """
    try:
        from systems.equipment.equipment_effects import hero_enemy_type_resistance
        return hero_enemy_type_resistance(hero, enemy_type)
    except Exception:
        multiplier = 1.0
        for item in list(getattr(hero, "equipment", {}).values()):
            multiplier *= 1.0 - float(
                getattr(item, "enemy_type_resistance", {}).get(enemy_type, 0.0)
            )
        return max(0.35, multiplier)


def effective_power_against_enemy(hero, enemy_type: str, base_power: int) -> int:
    return max(1, int(int(base_power) * hero_matchup_multiplier(hero, enemy_type)))


# ---------------------------------------------------------------------------
# Item–enemy relevance
# ---------------------------------------------------------------------------

def item_matches_enemy_type(item, enemy_type: str) -> bool:
    """
    Return True if this item has any meaningful interaction with the given
    enemy type.  Checks affinity, bonuses, resistances, and damage type
    cross-reference against the enemy's weak_to list.
    """
    try:
        from systems.equipment.equipment_effects import item_relevant_for_enemy
        if item_relevant_for_enemy(item, enemy_type):
            return True
    except Exception:
        if enemy_type in list(getattr(item, "enemy_affinity", [])):
            return True
        if enemy_type in dict(getattr(item, "enemy_type_bonus", {})):
            return True
        if enemy_type in dict(getattr(item, "enemy_type_resistance", {})):
            return True

    # Check if this item's damage type is effective against the enemy.
    rules   = enemy_rules(enemy_type)
    weak_to = set(rules.get("weak_to", []))
    for damage_type in dict(getattr(item, "damage_type_bonus", {})).keys():
        if damage_type in weak_to:
            return True

    return False


# ---------------------------------------------------------------------------
# Party summary (for UI / dev console)
# ---------------------------------------------------------------------------

def party_matchup_summary(party, enemy_type: str) -> List[str]:
    lines: List[str] = []
    rules = enemy_rules(enemy_type)

    lines.append(info(f"Enemy Type: {enemy_type} — {rules.get('description', '')}"))

    weak_to = list(rules.get("weak_to", []))
    resists = list(rules.get("resists", []))

    if weak_to:
        lines.append(success(f"Weak to: {', '.join(weak_to)}"))
    if resists:
        lines.append(warning(f"Resists: {', '.join(resists)}"))

    for hero in party:
        damage_type        = damage_type_for_hero(hero)
        attack_multiplier  = hero_matchup_multiplier(hero, enemy_type)
        defense_multiplier = incoming_damage_multiplier(hero, enemy_type)

        if attack_multiplier > 1.05:
            lines.append(
                success(f"{hero.name}: {damage_type} damage is effective (×{attack_multiplier:.2f}).")
            )
        elif attack_multiplier < 0.95:
            lines.append(
                warning(f"{hero.name}: {damage_type} damage is resisted (×{attack_multiplier:.2f}).")
            )
        else:
            lines.append(
                info(f"{hero.name}: {damage_type} damage is neutral (×{attack_multiplier:.2f}).")
            )

        if defense_multiplier < 0.95:
            lines.append(
                success(
                    f"{hero.name}: gear reduces incoming {enemy_type} damage "
                    f"(×{defense_multiplier:.2f})."
                )
            )

    return lines