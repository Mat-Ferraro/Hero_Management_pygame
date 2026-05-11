"""
models/hero.py

Hero dataclass — the canonical in-memory representation of a guild member.

Changes from previous version:
  - contract_attitude default changed from "Practical" → "Pragmatic" (v11 names).
  - combat_power() now calls equipment_effects.equipment_power_bonus() instead
    of summing raw stat_bonuses inline.  This picks up synergy bonuses too.
  - Added equip_capacity_bonus field (default 0) so progression systems can
    raise a hero's equipment capacity without touching equipment_rules directly.
  - total_stat() and career_stage() / age_power_multiplier() helpers added —
    referenced by inventory_scene and other UI but were missing from this class.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.contract_attitudes import attitude_description
from core.growth_rates import growth_description, growth_multiplier
from core.hero_specialties import specialty_description


STAT_NAMES = ("might", "agility", "mind", "spirit")


@dataclass
class Hero:
    # ------------------------------------------------------------------
    # Required identity fields
    # ------------------------------------------------------------------
    name: str
    hero_class: str
    age: int
    level: int
    xp: int
    stats: Dict[str, int]
    signing_bonus: int
    wage_per_year: int
    contract_years: int

    # ------------------------------------------------------------------
    # Optional identity fields
    # ------------------------------------------------------------------
    specialty: str = "Adventurer"
    growth_rate: str = "Talented"
    contract_attitude: str = "Pragmatic"   # v11 default (was "Practical")

    # ------------------------------------------------------------------
    # Equipment
    # ------------------------------------------------------------------
    equipment: Dict[str, object] = field(default_factory=dict)
    # Keys are category names ("Weapon", "Armor", "Utility", "Trinket").
    # Values are Item instances.

    equip_capacity_bonus: int = 0
    # Added by progression or guild upgrades to raise the hero's slot cap.

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    injured_years_remaining: int = 0
    wound_history: List[str] = field(default_factory=list)
    current_health: Optional[int] = None
    debt: int = 0
    is_temporary_survivor: bool = False
    satisfaction: int = 80
    participated_this_cycle: bool = False

    # ------------------------------------------------------------------
    # Progression
    # ------------------------------------------------------------------
    subclass: Optional[str] = None
    special_ability: Optional[str] = None

    training_points: int = 0
    training_path_progress: Dict[str, int] = field(default_factory=dict)
    unlocked_subclasses: List[str] = field(default_factory=list)
    unlocked_abilities: List[str] = field(default_factory=list)
    primary_subclass: Optional[str] = None

    # ------------------------------------------------------------------
    # Normalisation
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        self.age = int(self.age)
        self.level = max(1, int(self.level))
        self.xp = max(0, int(self.xp))
        self.signing_bonus = max(0, int(self.signing_bonus))
        self.wage_per_year = max(0, int(self.wage_per_year))
        self.contract_years = max(0, int(self.contract_years))
        self.injured_years_remaining = max(0, int(self.injured_years_remaining))
        self.debt = max(0, int(self.debt))
        self.satisfaction = max(0, min(100, int(self.satisfaction)))
        self.equip_capacity_bonus = max(0, int(self.equip_capacity_bonus))

        normalized: Dict[str, int] = {}
        for stat_name in STAT_NAMES:
            normalized[stat_name] = max(0, int(self.stats.get(stat_name, 0)))
        self.stats = normalized

        if self.current_health is not None:
            self.current_health = max(0, int(self.current_health))

        self.training_points = max(0, int(self.training_points))
        self.training_path_progress = {
            str(k): max(0, int(v))
            for k, v in dict(self.training_path_progress).items()
        }
        self.unlocked_subclasses = [str(v) for v in self.unlocked_subclasses]
        self.unlocked_abilities  = [str(v) for v in self.unlocked_abilities]
        self.wound_history       = [str(v) for v in self.wound_history]

    # ------------------------------------------------------------------
    # Stat helpers
    # ------------------------------------------------------------------

    def stat_total(self) -> int:
        return sum(int(self.stats.get(s, 0)) for s in STAT_NAMES)

    def total_stat(self, stat_name: str) -> int:
        """Base stat value (no career phase modifier, no equipment)."""
        return int(self.stats.get(stat_name, 0))

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def max_health(self) -> int:
        base = 40
        base += self.level * 6
        base += int(self.stats.get("might", 0)) * 2
        base += int(self.stats.get("spirit", 0))
        if self.hero_class == "Warrior":
            base += 8
        elif self.hero_class == "Cleric":
            base += 4
        elif self.hero_class == "Mage":
            base -= 2
        return max(1, base)

    def reset_health_for_expedition(self) -> None:
        self.current_health = self.max_health()

    def health_percent(self) -> float:
        if self.current_health is None:
            return 1.0
        maximum = self.max_health()
        if maximum <= 0:
            return 0.0
        return max(0.0, min(1.0, float(self.current_health) / float(maximum)))

    def health_status(self) -> str:
        if self.current_health is None:
            return "HEALTHY"
        if self.current_health <= 0:
            return "DEAD"
        ratio = self.health_percent()
        if ratio <= 0.10:
            return "CRITICAL"
        if ratio <= 0.35:
            return "WOUNDED"
        if ratio <= 0.65:
            return "HURT"
        return "HEALTHY"

    # ------------------------------------------------------------------
    # Combat power
    # ------------------------------------------------------------------

    def combat_power(self) -> int:
        might   = int(self.stats.get("might", 0))
        agility = int(self.stats.get("agility", 0))
        mind    = int(self.stats.get("mind", 0))
        spirit  = int(self.stats.get("spirit", 0))

        if self.hero_class == "Warrior":
            primary = (might * 3) + spirit
        elif self.hero_class == "Rogue":
            primary = (agility * 3) + mind
        elif self.hero_class == "Cleric":
            primary = (spirit * 3) + mind
        else:
            primary = (mind * 3) + spirit

        general = might + agility + mind + spirit

        # Use equipment_effects so synergy bonuses are included.
        # Guard against circular import by importing lazily.
        try:
            from systems.equipment.equipment_effects import equipment_power_bonus
            gear_bonus = equipment_power_bonus(self)
        except Exception:
            # Fallback: raw stat sum across equipped items (no synergy).
            gear_bonus = sum(
                sum(int(v) for v in getattr(item, "stat_bonuses", {}).values())
                for item in self.equipment.values()
            )

        base_power   = primary + general + gear_bonus + (self.level * 4)
        scaled_power = int(round(base_power * growth_multiplier(self.growth_rate)))

        if self.injured_years_remaining > 0:
            scaled_power = int(round(scaled_power * 0.85))

        return max(1, scaled_power)

    # ------------------------------------------------------------------
    # Career / age helpers (used by UI scenes)
    # ------------------------------------------------------------------

    def career_stage(self) -> str:
        """Human-readable career phase label without importing hero_career."""
        from systems.progression.hero_career import career_phase_name
        return career_phase_name(self)

    def age_power_multiplier(self) -> float:
        """
        Approximate age-based power scaling for UI display.
        Mirrors the phase modifier concept without importing the full table.
        """
        from systems.progression.hero_career import phase_modifiers_for_hero
        mods = phase_modifiers_for_hero(self)
        total_mod = sum(mods.values())
        # Each stat point ≈ 1 power unit; express as a multiplier around 1.0.
        base_stats = max(1, self.stat_total())
        return max(0.5, 1.0 + (total_mod / base_stats))

    # ------------------------------------------------------------------
    # Damage / healing
    # ------------------------------------------------------------------

    def take_damage(self, amount: int) -> str:
        damage = max(0, int(amount))
        if self.current_health is None:
            self.reset_health_for_expedition()
        assert self.current_health is not None
        old = self.current_health
        self.current_health = max(0, self.current_health - damage)
        return (
            f"{self.name} takes {damage} damage "
            f"({old}→{self.current_health}/{self.max_health()} HP)."
        )

    def heal(self, amount: int) -> str:
        healing = max(0, int(amount))
        if self.current_health is None:
            self.reset_health_for_expedition()
        assert self.current_health is not None
        old = self.current_health
        self.current_health = min(self.max_health(), self.current_health + healing)
        gained = self.current_health - old
        return (
            f"{self.name} heals {gained} HP "
            f"({old}→{self.current_health}/{self.max_health()} HP)."
        )

    # ------------------------------------------------------------------
    # Wounds
    # ------------------------------------------------------------------

    def apply_minor_wound(self) -> str:
        self.injured_years_remaining = max(self.injured_years_remaining, 1)
        self.wound_history.append("Minor wound")
        return f"{self.name} suffered a minor wound."

    def apply_mortal_wound(self) -> str:
        self.injured_years_remaining = max(self.injured_years_remaining, 2)
        self.wound_history.append("Mortal wound")
        return f"{self.name} suffered a mortal wound."

    # ------------------------------------------------------------------
    # Satisfaction
    # ------------------------------------------------------------------

    def adjust_satisfaction(self, delta: int, reason: str = "") -> int:
        old = self.satisfaction
        self.satisfaction = max(0, min(100, self.satisfaction + int(delta)))
        return self.satisfaction - old

    # ------------------------------------------------------------------
    # XP / levelling
    # ------------------------------------------------------------------

    def xp_to_next_level(self) -> int:
        return 100 + ((self.level - 1) * 50)

    def add_xp(self, amount: int) -> List[str]:
        gained = max(0, int(amount))
        messages: List[str] = []
        if gained <= 0:
            return messages
        self.xp += gained
        messages.append(f"{self.name} gained {gained} XP.")
        while self.xp >= self.xp_to_next_level():
            self.xp -= self.xp_to_next_level()
            self.level += 1
            messages.extend(self._apply_level_up())
        return messages

    def _apply_level_up(self) -> List[str]:
        messages = [f"{self.name} reached level {self.level}!"]
        priority = {
            "Warrior": ["might", "spirit"],
            "Rogue":   ["agility", "mind"],
            "Cleric":  ["spirit", "mind"],
        }.get(self.hero_class, ["mind", "spirit"])
        self.stats[priority[0]] = self.stats.get(priority[0], 0) + 1
        self.stats[priority[1]] = self.stats.get(priority[1], 0) + 1
        messages.append(f"{self.name}'s {priority[0]} and {priority[1]} improved.")
        self.reset_health_for_expedition()
        return messages

    # ------------------------------------------------------------------
    # Time
    # ------------------------------------------------------------------

    def advance_time(self, years: int) -> List[str]:
        elapsed = max(0, int(years))
        messages: List[str] = []
        if elapsed <= 0:
            return messages
        self.age += elapsed
        if self.injured_years_remaining > 0:
            old = self.injured_years_remaining
            self.injured_years_remaining = max(0, self.injured_years_remaining - elapsed)
            if old > 0 and self.injured_years_remaining == 0:
                messages.append(f"{self.name} has recovered from injuries.")
        return messages

    def should_retire(self) -> bool:
        return self.age >= {
            "Warrior": 52,
            "Rogue":   55,
            "Cleric":  70,
            "Mage":    88,
        }.get(self.hero_class, 60)

    # ------------------------------------------------------------------
    # Mentorship
    # ------------------------------------------------------------------

    def satisfaction_label(self) -> str:
        """Short human-readable label for current satisfaction level.
        Matches the three tiers used by management_scene.satisfaction_style()."""
        if self.satisfaction >= 75:
            return "Content"
        if self.satisfaction >= 45:
            return "Restless"
        return "Unhappy"

    def retirement_chance(self) -> float:
        """
        Estimated probability (0.0–1.0) that this hero retires soon.
        Used for display in management/market scenes as a risk indicator.
        Returns 1.0 if the hero already meets retirement age criteria.
        Returns 0.0 if they are far from retirement.
        Scales linearly over the last 10 years of their career.
        """
        retirement_ages = {
            "Warrior": 52,
            "Rogue":   55,
            "Cleric":  70,
            "Mage":    88,
        }
        retire_at = retirement_ages.get(self.hero_class, 60)

        if self.age >= retire_at:
            return 1.0

        years_left = retire_at - self.age
        if years_left >= 10:
            return 0.0

        return max(0.0, min(1.0, 1.0 - (years_left / 10.0)))

    def mentorship_value(self) -> int:
        if self.level >= 7: return 3
        if self.level >= 5: return 2
        if self.level >= 3: return 1
        return 0

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def display_short(self) -> str:
        health_text  = ""
        if self.current_health is not None:
            health_text = f" | HP {self.current_health}/{self.max_health()} | {self.health_status()}"
        subclass_text = f" | {self.subclass}" if self.subclass else ""
        ability_text  = f" | {self.special_ability}" if self.special_ability else ""
        return (
            f"{self.name} | {self.hero_class} Lv{self.level}{subclass_text}{ability_text} | "
            f"Age {self.age} | "
            f"M {self.stats.get('might', 0)} "
            f"A {self.stats.get('agility', 0)} "
            f"Mi {self.stats.get('mind', 0)} "
            f"S {self.stats.get('spirit', 0)} | "
            f"{self.specialty} | {self.growth_rate}{health_text}"
        )

    def display(self) -> str:
        equipment_names = (
            ", ".join(item.name for item in self.equipment.values()) or "None"
        )
        lines = [
            f"Name: {self.name}",
            f"Class: {self.hero_class}",
            f"Level: {self.level}",
            f"Age: {self.age}",
            f"Stats: {self.stats}",
            f"Combat Power: {self.combat_power()}",
            f"Specialty: {self.specialty} - {specialty_description(self.specialty)}",
            f"Growth: {self.growth_rate} - {growth_description(self.growth_rate)}",
            f"Contract Attitude: {self.contract_attitude} - {attitude_description(self.contract_attitude)}",
            f"Signing Bonus: {self.signing_bonus}g",
            f"Wage: {self.wage_per_year}g",
            f"Contract Years: {self.contract_years}",
            f"Debt: {self.debt}g",
            f"Satisfaction: {self.satisfaction}",
            f"Equipment: {equipment_names}",
        ]
        if self.subclass:        lines.append(f"Subclass: {self.subclass}")
        if self.primary_subclass: lines.append(f"Primary Subclass: {self.primary_subclass}")
        if self.special_ability:  lines.append(f"Special Ability: {self.special_ability}")
        if self.unlocked_subclasses:
            lines.append(f"Unlocked Subclasses: {', '.join(self.unlocked_subclasses)}")
        if self.unlocked_abilities:
            lines.append(f"Unlocked Abilities: {', '.join(self.unlocked_abilities)}")
        if self.wound_history:
            lines.append(f"Wound History: {', '.join(self.wound_history)}")
        return "\n".join(lines)