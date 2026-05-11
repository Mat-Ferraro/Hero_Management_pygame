"""
systems/equipment/equipment_rules.py

Single source of truth for what a hero can and cannot equip.

Design constraints (GDD/TDD):
  - Heroes start with equip_capacity = 2, raised through progression.
  - One item maximum per category (Weapon / Armor / Utility / Trinket).
  - Capacity is measured by sum of equip_capacity_cost across equipped items,
    so a heavy 2-slot item uses half the budget by itself.
  - Equipment changes only happen between campaigns (management phase).
  - On retirement / departure, all gear returns to guild inventory via unequip_all.
  - Consumables cannot be equipped; they are activated from inventory directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from models import Hero, Item


BASE_EQUIP_CAPACITY = 2
MAX_EQUIP_CAPACITY  = 4
VALID_CATEGORIES    = ("Weapon", "Armor", "Utility", "Trinket")


# ---------------------------------------------------------------------------
# Capacity
# ---------------------------------------------------------------------------

def hero_equip_capacity(hero: Hero) -> int:
    base  = BASE_EQUIP_CAPACITY
    bonus = int(getattr(hero, "equip_capacity_bonus", 0))
    return min(MAX_EQUIP_CAPACITY, base + bonus)


def hero_slots_used(hero: Hero) -> int:
    return sum(int(getattr(item, "equip_capacity_cost", 1)) for item in hero.equipment.values())


def hero_slots_remaining(hero: Hero) -> int:
    return max(0, hero_equip_capacity(hero) - hero_slots_used(hero))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

@dataclass
class EquipResult:
    success: bool
    message: str
    displaced_item: Optional[Item] = None


def can_equip(hero: Hero, item: Item) -> Tuple[bool, str]:
    """Check whether hero can equip item. Returns (ok, reason)."""
    if item.consumable:
        return False, f"{item.name} is a consumable — activate it from inventory."

    if item.category not in VALID_CATEGORIES:
        return False, f"Unknown item category '{item.category}'."

    if not item.can_equip(hero.hero_class):
        return False, f"{item.name} can only be equipped by: {', '.join(item.class_restrictions)}."

    current = hero.equipment.get(item.category)
    new_cost = int(getattr(item, "equip_capacity_cost", 1))

    if current is not None:
        old_cost   = int(getattr(current, "equip_capacity_cost", 1))
        net_change = new_cost - old_cost
        if hero_slots_remaining(hero) < net_change:
            return False, (
                f"Equipping {item.name} would exceed {hero.name}'s capacity "
                f"({hero_equip_capacity(hero)} slots)."
            )
    else:
        if new_cost > hero_slots_remaining(hero):
            return False, (
                f"{item.name} costs {new_cost} slot(s); "
                f"{hero.name} has {hero_slots_remaining(hero)} remaining."
            )

    return True, ""


def equip_item(hero: Hero, item: Item, guild_inventory: List[Item]) -> EquipResult:
    """
    Equip item to hero.  Item must already be in guild_inventory.
    Any displaced item is returned to guild_inventory.
    """
    ok, reason = can_equip(hero, item)
    if not ok:
        return EquipResult(success=False, message=reason)

    if item not in guild_inventory:
        return EquipResult(success=False, message=f"{item.name} is not in guild inventory.")

    displaced: Optional[Item] = None
    current = hero.equipment.get(item.category)

    if current is not None:
        hero.equipment.pop(item.category)
        guild_inventory.append(current)
        displaced = current

    guild_inventory.remove(item)
    hero.equipment[item.category] = item

    msg = (
        f"Equipped {item.name}; returned {displaced.name} to inventory."
        if displaced else
        f"Equipped {item.name} to {hero.name}."
    )
    return EquipResult(success=True, message=msg, displaced_item=displaced)


def unequip_item(hero: Hero, category: str, guild_inventory: List[Item]) -> EquipResult:
    """Remove item in category from hero and return it to guild_inventory."""
    if category not in hero.equipment:
        return EquipResult(success=False, message=f"{hero.name} has nothing in {category}.")
    item = hero.equipment.pop(category)
    guild_inventory.append(item)
    return EquipResult(success=True, message=f"Unequipped {item.name} from {hero.name}.")


def unequip_all(hero: Hero, guild_inventory: List[Item]) -> List[Item]:
    """Move ALL of hero's gear to guild_inventory. Used on retirement/departure."""
    moved = list(hero.equipment.values())
    for item in moved:
        guild_inventory.append(item)
    hero.equipment.clear()
    return moved


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def loadout_summary(hero: Hero) -> Dict[str, str]:
    return {cat: hero.equipment[cat].name if cat in hero.equipment else "—" for cat in VALID_CATEGORIES}


def capacity_display(hero: Hero) -> str:
    return f"{hero_slots_used(hero)}/{hero_equip_capacity(hero)} slots"