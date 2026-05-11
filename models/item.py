"""
models/item.py

Item dataclass — the canonical representation of a piece of equipment
owned by the guild.

Design intent
-------------
- The guild owns all items.  Heroes equip references to guild inventory;
  they do not own items personally.
- Items are grouped into four categories: Weapon, Armor, Utility, Trinket.
  A hero may equip at most one item per category, subject to their current
  equip capacity (starts at 2, grows through progression).
- Most fields are handcrafted in items.json rather than procedurally
  generated.  The schema is intentionally stable so that item identity
  persists across saves.
- Tags drive broad synergy rules rather than narrow named-item pair sets.
  An item that "gains a bonus when equipped alongside any weapon" uses a
  tag condition, not a specific item reference.
- Drawbacks make items genuinely interesting — a cursed item might impose
  a penalty alongside its power, rather than being pure upside.
- Consumables are one-time-use items removed from the guild inventory on
  activation.  They are tracked separately from equipped gear.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_CATEGORIES = ("Weapon", "Armor", "Utility", "Trinket")

VALID_RARITIES = ("Common", "Uncommon", "Rare", "Epic", "Legendary")


# ---------------------------------------------------------------------------
# Item
# ---------------------------------------------------------------------------

@dataclass
class Item:
    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name: str
    category: str           # "Weapon" | "Armor" | "Utility" | "Trinket"
    rarity: str = "Common"
    lore: str = ""          # Flavour text.  Short — one sentence.

    # ------------------------------------------------------------------
    # Mechanical effects (all optional / empty by default)
    # ------------------------------------------------------------------
    stat_bonuses: Dict[str, int] = field(default_factory=dict)
    # Flat dispatch-stat bonuses applied when the item is equipped.
    # Keys are dispatch stat names: might, guard, wit, presence, swift.

    damage_type_bonus: Dict[str, float] = field(default_factory=dict)
    # Multiplier bonuses to outgoing damage of a given type.
    # e.g. {"Physical": 0.10} → +10% physical damage output.

    enemy_type_bonus: Dict[str, float] = field(default_factory=dict)
    # Multiplier bonuses vs a specific enemy type.

    enemy_type_resistance: Dict[str, float] = field(default_factory=dict)
    # Multiplier reductions to incoming damage from a specific enemy type.
    # e.g. {"Dragons": 0.20} → −20% damage taken from Dragons.

    # ------------------------------------------------------------------
    # Tags — broad categorical labels used by the synergy engine.
    # Examples: "holy", "shadow", "blade", "shield", "arcane",
    #           "ranged", "heavy", "light", "cursed", "blessed"
    # ------------------------------------------------------------------
    tags: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Drawbacks — mechanical penalties paired with power.
    # Each entry is a human-readable description of the cost.
    # The engine reads these for display; future systems may parse them.
    # ------------------------------------------------------------------
    drawbacks: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Synergy conditions — broad tag-based rules.
    # Each entry is a dict describing one condition:
    #   {
    #     "requires_tag": "blade",      # item must co-equip with tagged item
    #     "stat": "might",              # which stat is boosted
    #     "bonus": 2,                   # by how much
    #     "description": "..."          # readable explanation
    #   }
    # Conditions are evaluated by equipment_synergies.py at equip time.
    # ------------------------------------------------------------------
    synergy_conditions: List[Dict] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Restrictions
    # ------------------------------------------------------------------
    class_restrictions: List[str] = field(default_factory=list)
    # Empty = any class may equip.

    enemy_affinity: List[str] = field(default_factory=list)
    # Informational: which enemy types this item is particularly suited to.

    # ------------------------------------------------------------------
    # Special flags
    # ------------------------------------------------------------------
    consumable: bool = False
    # If True, the item is removed from the guild inventory on use.

    equip_capacity_cost: int = 1
    # Most items cost 1 slot.  Rare powerful items may cost 2.

    # ------------------------------------------------------------------
    # Upgrade / provenance
    # ------------------------------------------------------------------
    upgrade_from: Optional[str] = None
    # Name of the base item this was upgraded from, if any.

    upgrade_paths: List[str] = field(default_factory=list)
    # Names of items this can be upgraded into.

    story_flags: List[str] = field(default_factory=list)
    # Tags set by campaign events: "recovered", "cursed_deep", "named", etc.

    # ------------------------------------------------------------------
    # Economy
    # ------------------------------------------------------------------
    value: int = 0
    # Base gold value for sell/buy calculations.

    # ------------------------------------------------------------------
    # Backward-compat shim
    # ------------------------------------------------------------------
    # Old code used `slot` (free string).  We keep a property so nothing
    # hard-crashes during the transition.  Remove after full migration.
    @property
    def slot(self) -> str:
        return self.category.lower()

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        self.value = max(0, int(self.value))
        self.equip_capacity_cost = max(1, int(self.equip_capacity_cost))

        # Normalise category capitalisation.
        if self.category:
            self.category = self.category.capitalize()

    def can_equip(self, hero_class: str) -> bool:
        return not self.class_restrictions or hero_class in self.class_restrictions

    def is_cursed(self) -> bool:
        return "cursed" in self.tags

    def is_consumable(self) -> bool:
        return self.consumable

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def stat_bonus_summary(self) -> str:
        parts = []
        for stat, value in self.stat_bonuses.items():
            parts.append(f"+{value} {stat}")
        for damage_type, value in self.damage_type_bonus.items():
            parts.append(f"+{int(value * 100)}% {damage_type} dmg")
        for enemy, value in self.enemy_type_bonus.items():
            parts.append(f"+{int(value * 100)}% vs {enemy}")
        for enemy, value in self.enemy_type_resistance.items():
            parts.append(f"-{int(value * 100)}% from {enemy}")
        return "; ".join(parts) if parts else "No bonuses"

    def display(self) -> str:
        parts = [
            f"{self.name}",
            f"[{self.rarity} {self.category}]",
            f"({self.stat_bonus_summary()})",
            f"— {self.value}g",
        ]
        if self.class_restrictions:
            parts.append(f"| Classes: {', '.join(self.class_restrictions)}")
        if self.drawbacks:
            parts.append(f"| Drawback: {'; '.join(self.drawbacks)}")
        if self.consumable:
            parts.append("| CONSUMABLE")
        if self.equip_capacity_cost > 1:
            parts.append(f"| Costs {self.equip_capacity_cost} slots")
        return " ".join(parts)

    def tag_list_display(self) -> str:
        return ", ".join(self.tags) if self.tags else "—"