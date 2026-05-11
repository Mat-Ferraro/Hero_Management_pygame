"""
systems/equipment/equipment_effects.py

Applies item stat bonuses and active synergy bonuses to a hero's effective
dispatch stats and combat multipliers.

This is the bridge between the equipment system and the campaign/combat
systems.  All equipment reads during task scoring and combat resolution
should go through this module rather than reading hero.equipment directly.

Dispatch stats (used by task_scoring.py):
    might, guard, wit, presence, swift

Combat multipliers (used by combat_types.py):
    damage_type_bonus, enemy_type_bonus, enemy_type_resistance
"""

from __future__ import annotations

from typing import Any, Dict, List

from models import Hero, Item
from systems.equipment.equipment_synergies import synergy_stat_bonuses


# ---------------------------------------------------------------------------
# Dispatch stat bonuses from equipment
# ---------------------------------------------------------------------------

DISPATCH_STATS = ("might", "guard", "wit", "presence", "swift")


def item_dispatch_bonuses(item: Item) -> Dict[str, int]:
    """
    Extract dispatch-stat bonuses from a single item's stat_bonuses dict.
    Only returns keys that are recognised dispatch stats.
    """
    return {
        stat: int(item.stat_bonuses.get(stat, 0))
        for stat in DISPATCH_STATS
        if stat in item.stat_bonuses
    }


def equipment_dispatch_bonuses(hero: Hero) -> Dict[str, int]:
    """
    Sum of all dispatch-stat bonuses from equipped items, including active
    synergy bonuses.  This is the total additive equipment contribution.
    """
    totals: Dict[str, int] = {stat: 0 for stat in DISPATCH_STATS}

    # Direct item bonuses.
    for item in hero.equipment.values():
        for stat, value in item_dispatch_bonuses(item).items():
            totals[stat] = totals.get(stat, 0) + value

    # Synergy bonuses (only dispatch stats — filter others out).
    for stat, value in synergy_stat_bonuses(hero).items():
        if stat in totals:
            totals[stat] += value

    return {stat: v for stat, v in totals.items() if v != 0}


def apply_equipment_to_dispatch_stats(
    base_stats: Dict[str, int], hero: Hero
) -> Dict[str, int]:
    """
    Return a new dispatch stat dict with equipment bonuses added.
    Does NOT mutate base_stats.
    """
    bonuses = equipment_dispatch_bonuses(hero)
    result  = dict(base_stats)
    for stat, bonus in bonuses.items():
        result[stat] = result.get(stat, 0) + bonus
    return result


# ---------------------------------------------------------------------------
# Combat multipliers from equipment
# ---------------------------------------------------------------------------

def equipped_items(hero: Hero) -> List[Item]:
    return list(hero.equipment.values())


def hero_damage_type_multiplier(hero: Hero, damage_type: str) -> float:
    """
    Combined damage-type multiplier from all equipped items.
    Each item's bonus is additive as a percentage modifier:
    final = product of (1.0 + bonus_i) for all items with that damage type.
    """
    multiplier = 1.0
    for item in equipped_items(hero):
        bonus = float(item.damage_type_bonus.get(damage_type, 0.0))
        if bonus:
            multiplier *= 1.0 + bonus
    return multiplier


def hero_enemy_type_multiplier(hero: Hero, enemy_type: str) -> float:
    """Combined outgoing bonus multiplier vs a specific enemy type."""
    multiplier = 1.0
    for item in equipped_items(hero):
        bonus = float(item.enemy_type_bonus.get(enemy_type, 0.0))
        if bonus:
            multiplier *= 1.0 + bonus
    return multiplier


def hero_enemy_type_resistance(hero: Hero, enemy_type: str) -> float:
    """
    Combined incoming damage reduction from a specific enemy type.
    Each item's resistance is a fraction subtracted from 1.0:
    final = product of (1.0 - resist_i).
    Clamped to a minimum of 0.35 so resistance is never total.
    """
    multiplier = 1.0
    for item in equipped_items(hero):
        resist = float(item.enemy_type_resistance.get(enemy_type, 0.0))
        if resist:
            multiplier *= 1.0 - resist
    return max(0.35, multiplier)


# ---------------------------------------------------------------------------
# Effective combat power contribution from equipment
# ---------------------------------------------------------------------------

def equipment_power_bonus(hero: Hero) -> int:
    """
    Flat combat-power contribution from all stat bonuses on equipped items
    plus active synergy bonuses.  Used by Hero.combat_power() as an additive
    term alongside the stat-based calculation.

    Maps dispatch stats to combat-power weight:
        might    → 2 pts per point (primary physical)
        guard    → 1 pt  (defensive, partial contribution)
        wit      → 2 pts (primary magical)
        presence → 1 pt
        swift    → 1 pt
    """
    WEIGHTS = {"might": 2, "guard": 1, "wit": 2, "presence": 1, "swift": 1}
    bonuses = equipment_dispatch_bonuses(hero)
    return sum(int(bonuses.get(stat, 0)) * weight for stat, weight in WEIGHTS.items())


# ---------------------------------------------------------------------------
# Drawback summary (for UI display and future mechanical hooks)
# ---------------------------------------------------------------------------

def active_drawbacks(hero: Hero) -> List[str]:
    """Return all drawback descriptions from the hero's equipped items."""
    result = []
    for item in equipped_items(hero):
        result.extend(item.drawbacks)
    return result


# ---------------------------------------------------------------------------
# Item–enemy matchup (replaces item_matches_enemy_type in combat_types.py)
# ---------------------------------------------------------------------------

def item_relevant_for_enemy(item: Item, enemy_type: str) -> bool:
    """
    Return True if this item has any meaningful interaction with the given
    enemy type — bonus, resistance, or affinity tag.
    """
    if enemy_type in item.enemy_affinity:
        return True
    if enemy_type in item.enemy_type_bonus:
        return True
    if enemy_type in item.enemy_type_resistance:
        return True
    return False