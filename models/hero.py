from dataclasses import dataclass, field
from typing import Dict, List, Optional

from combat_types import damage_type_for_hero
from growth_rates import growth_description, growth_multiplier
from contract_attitudes import attitude_description
from hero_specialties import specialty_description
from systems.age_curve import (
    age_power_multiplier,
    career_stage,
    career_summary,
    mentorship_value,
    retirement_age,
    retirement_pressure,
)
from .class_rules import CLASS_RULES, STAT_NAMES
from .item import Item
from ui import Color, pad_col


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
    equipment: Dict[str, Item] = field(default_factory=dict)
    injured_years_remaining: int = 0
    wound_history: List[str] = field(default_factory=list)
    current_health: Optional[int] = None
    debt: int = 0
    is_temporary_survivor: bool = False

    satisfaction: int = 80
    participated_this_cycle: bool = False

    subclass: Optional[str] = None
    special_ability: Optional[str] = None

    def total_stat(self, stat_name: str) -> int:
        total = self.stats.get(stat_name, 0)
        for item in self.equipment.values():
            total += item.stat_bonuses.get(stat_name, 0)
        return total

    def max_health(self) -> int:
        return 60 + (self.total_stat("might") * 4) + (self.total_stat("spirit") * 3) + (self.level * 8)

    def reset_health_for_expedition(self) -> None:
        self.current_health = self.max_health()

    def heal(self, amount: int) -> str:
        if self.current_health is None:
            self.reset_health_for_expedition()

        before = self.current_health
        self.current_health = min(self.max_health(), self.current_health + amount)
        healed = self.current_health - before
        return f"{self.name} recovered {healed} HP ({self.current_health}/{self.max_health()} HP)."

    def health_percent(self) -> float:
        if self.current_health is None:
            return 1.0
        return max(0.0, self.current_health / self.max_health())

    def health_status(self) -> str:
        percent = self.health_percent()
        if percent <= 0:
            return "DEAD"
        if percent < 0.25:
            return "CRITICAL"
        if percent < 0.50:
            return "WOUNDED"
        if percent < 0.75:
            return "HURT"
        return "Healthy"

    def career_stage(self) -> str:
        return career_stage(self)

    def age_power_multiplier(self) -> float:
        return age_power_multiplier(self)

    def mentorship_value(self) -> int:
        return mentorship_value(self)

    def retirement_age(self) -> int:
        return retirement_age(self)

    def satisfaction_label(self) -> str:
        if self.satisfaction >= 80:
            return "Happy"
        if self.satisfaction >= 50:
            return "Content"
        if self.satisfaction >= 25:
            return "Unhappy"
        if self.satisfaction > 0:
            return "Leaving Soon"
        return "Leaving"

    def adjust_satisfaction(self, amount: int, reason: str = "") -> str:
        old_value = self.satisfaction
        self.satisfaction = max(0, min(100, self.satisfaction + amount))

        if amount == 0:
            return ""

        sign = "+" if amount > 0 else ""
        reason_text = f" ({reason})" if reason else ""
        return (
            f"{self.name} satisfaction {sign}{amount}: "
            f"{old_value} -> {self.satisfaction} "
            f"[{self.satisfaction_label()}]{reason_text}."
        )

    def total_contract_value(self) -> int:
        return self.signing_bonus + (self.wage_per_year * self.contract_years)

    def combat_power(self) -> int:
        class_rules = CLASS_RULES[self.hero_class]

        primary = sum(self.total_stat(stat) * 3 for stat in class_rules["primary_stats"])
        secondary = sum(self.total_stat(stat) * 2 for stat in class_rules["secondary_stats"])
        general = sum(self.total_stat(stat) for stat in STAT_NAMES)

        raw_power = primary + secondary + general + self.level * 5

        injury_penalty = 0.65 if self.injured_years_remaining > 0 else 1.0
        age_multiplier = self.age_power_multiplier()

        subclass_bonus = 1.0
        if self.subclass:
            subclass_bonus += 0.04

        ability_bonus = 1.0
        if self.special_ability:
            ability_bonus += 0.03

        return max(1, int(raw_power * injury_penalty * age_multiplier * subclass_bonus * ability_bonus))

    def damage_type(self) -> str:
        return damage_type_for_hero(self)

    def growth_multiplier(self) -> float:
        return growth_multiplier(self.growth_rate)

    def xp_to_next_level(self) -> int:
        return 100 + (self.level - 1) * 60

    def add_xp(self, amount: int) -> List[str]:
        messages = []
        adjusted_amount = self.adjust_xp_for_age(amount)
        self.xp += adjusted_amount
        messages.append(f"{self.name} gained {adjusted_amount} XP.")

        while self.xp >= self.xp_to_next_level():
            self.xp -= self.xp_to_next_level()
            self.level += 1
            messages.extend(self.level_up())

        return messages

    def adjust_xp_for_age(self, base_xp: int) -> int:
        stage = self.career_stage()

        if stage == "Developing":
            multiplier = 1.20
        elif stage == "Prime":
            multiplier = 1.00
        elif stage == "Veteran":
            multiplier = 0.85
        else:
            if self.hero_class == "Mage":
                multiplier = 1.05
            else:
                multiplier = 0.65

        return max(1, int(base_xp * multiplier * self.growth_multiplier()))

    def level_up(self) -> List[str]:
        import random

        messages = [f"{self.name} reached level {self.level}!"]

        class_rules = CLASS_RULES[self.hero_class]

        for stat in class_rules["primary_stats"]:
            self.stats[stat] += 2
            messages.append(f"  +2 {stat}")

        for stat in class_rules["secondary_stats"]:
            self.stats[stat] += 1
            messages.append(f"  +1 {stat}")

        random_stat = random.choice(STAT_NAMES)
        self.stats[random_stat] += 1
        messages.append(f"  +1 {random_stat}")

        return messages

    def take_damage(self, amount: int) -> str:
        if self.current_health is None:
            self.reset_health_for_expedition()

        self.current_health = max(0, self.current_health - amount)
        return (
            f"{self.name} took {amount} damage "
            f"({self.current_health}/{self.max_health()} HP, {self.health_status()})."
        )

    def apply_minor_wound(self) -> str:
        import random

        duration_years = random.randint(1, 2)
        self.injured_years_remaining = max(self.injured_years_remaining, duration_years)
        wound = f"Minor wound: injured for {duration_years} year(s)"
        self.wound_history.append(wound)
        return f"{self.name} suffered a minor wound and will need {duration_years} year(s) to recover."

    def apply_mortal_wound(self) -> str:
        import random

        stat = random.choice(STAT_NAMES)
        loss = random.randint(1, 2)
        actual_loss = min(loss, max(0, self.stats[stat] - 1))
        self.stats[stat] -= actual_loss

        duration_years = random.randint(2, 4)
        self.injured_years_remaining = max(self.injured_years_remaining, duration_years)

        wound = f"Mortal wound: -{actual_loss} {stat}, injured for {duration_years} year(s)"
        self.wound_history.append(wound)
        return f"{self.name} suffered a mortal wound: -{actual_loss} {stat}, {duration_years} year recovery."

    def advance_time(self, years_passed: int) -> List[str]:
        messages = []

        self.contract_years -= years_passed

        if self.injured_years_remaining > 0:
            old_injury_years = self.injured_years_remaining
            self.injured_years_remaining = max(0, self.injured_years_remaining - years_passed)

            if self.injured_years_remaining == 0:
                messages.append(f"{self.name} recovered from injury after {old_injury_years} remaining year(s).")
            else:
                messages.append(f"{self.name} is still injured for {self.injured_years_remaining} more year(s).")

        old_age = self.age
        self.age += years_passed
        messages.append(f"{self.name} aged from {old_age} to {self.age}.")

        return messages

    def apply_aging(self, years_passed: int) -> List[str]:
        old_age = self.age
        self.age += years_passed
        return [f"{self.name} aged from {old_age} to {self.age}."]

    def retirement_chance(self) -> float:
        return retirement_pressure(self)

    def should_retire(self) -> bool:
        import random

        return random.random() < self.retirement_chance()

    def display_short(self, use_color: bool = True, include_money: bool = False) -> str:
        survivor_text = "TEMP" if self.is_temporary_survivor else ""

        injury_text = ""
        if self.injured_years_remaining > 0:
            injury_text = f"INJ {self.injured_years_remaining}y"

        debt_text = ""
        if self.debt > 0:
            debt_text = f"{self.debt}g"

        if self.current_health is None:
            hp_text = f"{self.max_health()}/{self.max_health()}"
            hp_status = "Healthy"
        else:
            hp_text = f"{self.current_health}/{self.max_health()}"
            hp_status = self.health_status()

        damage_text = self.damage_type()
        expedition_cost_text = f"{self.wage_per_year}g"
        satisfaction_text = f"{self.satisfaction}"
        subclass_text = self.subclass or "None"

        class_col = None
        damage_col = None
        growth_col = None
        terms_col = None
        status_col = None
        cost_col = None
        satisfaction_col = None

        if use_color:
            class_col = {
                "Warrior": Color.RED,
                "Rogue": Color.GREEN,
                "Cleric": Color.CYAN,
                "Mage": Color.MAGENTA,
            }.get(self.hero_class, Color.WHITE)

            damage_col = {
                "Physical": Color.YELLOW,
                "Magic": Color.MAGENTA,
                "Holy": Color.CYAN,
            }.get(damage_text, Color.WHITE)

            growth_col = {
                "Mundane": Color.DIM,
                "Talented": Color.WHITE,
                "Gifted": Color.GREEN,
                "Heroic": Color.CYAN,
                "Legendary": Color.MAGENTA,
                "Mythic": Color.RED,
            }.get(self.growth_rate, Color.WHITE)

            terms_col = {
                "Modest": Color.GREEN,
                "Practical": Color.WHITE,
                "Ambitious": Color.YELLOW,
                "Mercenary": Color.RED,
                "Noble": Color.CYAN,
            }.get(self.contract_attitude, Color.WHITE)

            status_col = {
                "DEAD": Color.RED,
                "CRITICAL": Color.RED,
                "WOUNDED": Color.YELLOW,
                "HURT": Color.YELLOW,
                "Healthy": Color.GREEN,
            }.get(hp_status, Color.WHITE)

            if self.wage_per_year >= 50:
                cost_col = Color.RED
            elif self.wage_per_year >= 30:
                cost_col = Color.YELLOW
            else:
                cost_col = Color.GREEN

            if self.satisfaction >= 75:
                satisfaction_col = Color.GREEN
            elif self.satisfaction >= 35:
                satisfaction_col = Color.YELLOW
            else:
                satisfaction_col = Color.RED

        columns = [
            pad_col(self.name, 18),
            pad_col(self.hero_class, 8, class_col),
            pad_col(subclass_text, 12),
            pad_col(self.specialty, 16),
            pad_col(damage_text, 8, damage_col),
            pad_col(self.growth_rate, 9, growth_col),
            pad_col(self.contract_attitude, 10, terms_col),
            pad_col(self.age, 3, align="right"),
            pad_col(self.career_stage(), 10),
            pad_col(f"Lv {self.level}", 5),
            pad_col(self.combat_power(), 5, align="right"),
            pad_col(hp_text, 9, align="right"),
            pad_col(hp_status, 17, status_col),
            pad_col(expedition_cost_text, 8, cost_col, align="right"),
            pad_col(satisfaction_text, 5, satisfaction_col, align="right"),
        ]

        if include_money:
            signing_col = None
            total_col = None

            if use_color:
                if self.signing_bonus >= 275:
                    signing_col = Color.RED
                elif self.signing_bonus >= 175:
                    signing_col = Color.YELLOW
                else:
                    signing_col = Color.GREEN

                total_value = self.total_contract_value()
                if total_value >= 700:
                    total_col = Color.RED
                elif total_value >= 400:
                    total_col = Color.YELLOW
                else:
                    total_col = Color.GREEN

            columns.extend(
                [
                    pad_col(f"{self.signing_bonus}g", 14, signing_col, align="right"),
                    pad_col(f"{self.total_contract_value()}g", 15, total_col, align="right"),
                ]
            )

        if debt_text:
            columns.append(pad_col(debt_text, 10, Color.RED if use_color else None))

        if survivor_text:
            columns.append(pad_col(survivor_text, 5))

        if injury_text:
            columns.append(pad_col(injury_text, 10, Color.YELLOW if use_color else None))

        return " | ".join(columns)

    def display_contract(self, use_color: bool = True) -> str:
        return self.display_short(use_color=use_color, include_money=True)

    def display_full(self) -> str:
        stat_text = ", ".join(f"{stat}: {self.total_stat(stat)}" for stat in STAT_NAMES)
        equipped = ", ".join(f"{slot}: {item.name}" for slot, item in self.equipment.items()) or "None"
        wounds = "; ".join(self.wound_history) or "None"
        retire_chance = self.retirement_chance() * 100

        return (
            f"{self.display_short()}\n"
            f"  Class: {self.hero_class}\n"
            f"  Subclass: {self.subclass or 'None'}\n"
            f"  Special Ability: {self.special_ability or 'None'}\n"
            f"  Career: {career_summary(self)}\n"
            f"  Mentorship Value: {self.mentorship_value()}\n"
            f"  Specialty: {self.specialty} - {specialty_description(self.specialty)}\n"
            f"  Growth Rate: {self.growth_rate} (x{self.growth_multiplier():.2f}) - {growth_description(self.growth_rate)}\n"
            f"  Contract Attitude: {self.contract_attitude} - {attitude_description(self.contract_attitude)}\n"
            f"  Satisfaction: {self.satisfaction}/100 ({self.satisfaction_label()})\n"
            f"  Damage Type: {self.damage_type()}\n"
            f"  XP: {self.xp}/{self.xp_to_next_level()}\n"
            f"  Stats: {stat_text}\n"
            f"  Equipment: {equipped}\n"
            f"  Wounds: {wounds}\n"
            f"  Debt: {self.debt}g\n"
            f"  Retirement Chance After Time Passes: {retire_chance:.1f}%\n"
        )