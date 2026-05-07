from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.contract_attitudes import attitude_description
from core.growth_rates import growth_description, growth_multiplier
from core.hero_specialties import specialty_description


STAT_NAMES = ("might", "agility", "mind", "spirit")


@dataclass
class Hero:
    name: str
    hero_class: str
    age: int
    level: int
    xp: int
    stats: Dict[str, int]
    signing_bonus: int
    wage_per_year: int
    contract_years: int
    specialty: str = "Adventurer"
    growth_rate: str = "Talented"
    contract_attitude: str = "Practical"

    equipment: Dict[str, object] = field(default_factory=dict)
    injured_years_remaining: int = 0
    wound_history: List[str] = field(default_factory=list)
    current_health: Optional[int] = None
    debt: int = 0
    is_temporary_survivor: bool = False
    satisfaction: int = 80
    participated_this_cycle: bool = False

    subclass: Optional[str] = None
    special_ability: Optional[str] = None

    training_points: int = 0
    training_path_progress: Dict[str, int] = field(default_factory=dict)
    unlocked_subclasses: List[str] = field(default_factory=list)
    unlocked_abilities: List[str] = field(default_factory=list)
    primary_subclass: Optional[str] = None

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

        normalized_stats: Dict[str, int] = {}
        for stat_name in STAT_NAMES:
            normalized_stats[stat_name] = max(0, int(self.stats.get(stat_name, 0)))
        self.stats = normalized_stats

        if self.current_health is not None:
            self.current_health = max(0, int(self.current_health))

        self.training_points = max(0, int(self.training_points))
        self.training_path_progress = {
            str(path_name): max(0, int(rank))
            for path_name, rank in dict(self.training_path_progress).items()
        }
        self.unlocked_subclasses = [str(value) for value in self.unlocked_subclasses]
        self.unlocked_abilities = [str(value) for value in self.unlocked_abilities]
        self.wound_history = [str(value) for value in self.wound_history]

    def stat_total(self) -> int:
        return sum(int(self.stats.get(stat_name, 0)) for stat_name in STAT_NAMES)

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

    def combat_power(self) -> int:
        might = int(self.stats.get("might", 0))
        agility = int(self.stats.get("agility", 0))
        mind = int(self.stats.get("mind", 0))
        spirit = int(self.stats.get("spirit", 0))

        if self.hero_class == "Warrior":
            primary = (might * 3) + spirit
        elif self.hero_class == "Rogue":
            primary = (agility * 3) + mind
        elif self.hero_class == "Cleric":
            primary = (spirit * 3) + mind
        else:
            primary = (mind * 3) + spirit

        general = might + agility + mind + spirit
        gear_bonus = sum(
            sum(int(value) for value in getattr(item, "stat_bonuses", {}).values())
            for item in self.equipment.values()
        )

        base_power = primary + general + gear_bonus + (self.level * 4)
        scaled_power = int(round(base_power * growth_multiplier(self.growth_rate)))

        if self.injured_years_remaining > 0:
            scaled_power = int(round(scaled_power * 0.85))

        return max(1, scaled_power)

    def take_damage(self, amount: int) -> str:
        damage = max(0, int(amount))

        if self.current_health is None:
            self.reset_health_for_expedition()

        assert self.current_health is not None
        old_health = self.current_health
        self.current_health = max(0, self.current_health - damage)

        return (
            f"{self.name} takes {damage} damage "
            f"({old_health}->{self.current_health}/{self.max_health()} HP)."
        )

    def heal(self, amount: int) -> str:
        healing = max(0, int(amount))

        if self.current_health is None:
            self.reset_health_for_expedition()

        assert self.current_health is not None
        old_health = self.current_health
        self.current_health = min(self.max_health(), self.current_health + healing)

        gained = self.current_health - old_health
        return (
            f"{self.name} heals {gained} HP "
            f"({old_health}->{self.current_health}/{self.max_health()} HP)."
        )

    def apply_minor_wound(self) -> str:
        self.injured_years_remaining = max(self.injured_years_remaining, 1)
        self.wound_history.append("Minor wound")
        return f"{self.name} suffered a minor wound."

    def apply_mortal_wound(self) -> str:
        self.injured_years_remaining = max(self.injured_years_remaining, 2)
        self.wound_history.append("Mortal wound")
        return f"{self.name} suffered a mortal wound."

    def adjust_satisfaction(self, delta: int, reason: str = "") -> int:
        old_value = self.satisfaction
        self.satisfaction = max(0, min(100, self.satisfaction + int(delta)))
        return self.satisfaction - old_value

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
            needed = self.xp_to_next_level()
            self.xp -= needed
            self.level += 1
            messages.extend(self._apply_level_up())

        return messages

    def _apply_level_up(self) -> List[str]:
        messages = [f"{self.name} reached level {self.level}!"]

        if self.hero_class == "Warrior":
            priority = ["might", "spirit"]
        elif self.hero_class == "Rogue":
            priority = ["agility", "mind"]
        elif self.hero_class == "Cleric":
            priority = ["spirit", "mind"]
        else:
            priority = ["mind", "spirit"]

        self.stats[priority[0]] = self.stats.get(priority[0], 0) + 1
        self.stats[priority[1]] = self.stats.get(priority[1], 0) + 1
        messages.append(
            f"{self.name}'s {priority[0]} and {priority[1]} improved."
        )

        self.reset_health_for_expedition()
        return messages

    def advance_time(self, years: int) -> List[str]:
        elapsed = max(0, int(years))
        messages: List[str] = []

        if elapsed <= 0:
            return messages

        self.age += elapsed

        if self.injured_years_remaining > 0:
            old_value = self.injured_years_remaining
            self.injured_years_remaining = max(0, self.injured_years_remaining - elapsed)
            if old_value > 0 and self.injured_years_remaining == 0:
                messages.append(f"{self.name} has recovered from injuries.")

        return messages

    def should_retire(self) -> bool:
        if self.hero_class == "Warrior":
            return self.age >= 52
        if self.hero_class == "Rogue":
            return self.age >= 55
        if self.hero_class == "Cleric":
            return self.age >= 70
        if self.hero_class == "Mage":
            return self.age >= 88
        return self.age >= 60

    def mentorship_value(self) -> int:
        if self.level >= 7:
            return 3
        if self.level >= 5:
            return 2
        if self.level >= 3:
            return 1
        return 0

    def display_short(self) -> str:
        health_text = ""
        if self.current_health is not None:
            health_text = f" | HP {self.current_health}/{self.max_health()} | {self.health_status()}"

        subclass_text = f" | {self.subclass}" if self.subclass else ""
        ability_text = f" | {self.special_ability}" if self.special_ability else ""

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
        equipment_names = ", ".join(item.name for item in self.equipment.values()) or "None"

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

        if self.subclass:
            lines.append(f"Subclass: {self.subclass}")
        if self.primary_subclass:
            lines.append(f"Primary Subclass: {self.primary_subclass}")
        if self.special_ability:
            lines.append(f"Special Ability: {self.special_ability}")
        if self.unlocked_subclasses:
            lines.append(f"Unlocked Subclasses: {', '.join(self.unlocked_subclasses)}")
        if self.unlocked_abilities:
            lines.append(f"Unlocked Abilities: {', '.join(self.unlocked_abilities)}")
        if self.wound_history:
            lines.append(f"Wound History: {', '.join(self.wound_history)}")

        return "\n".join(lines)