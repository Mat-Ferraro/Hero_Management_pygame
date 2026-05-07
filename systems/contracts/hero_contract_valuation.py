from __future__ import annotations

from typing import Dict


def base_combat_power(hero_class: str, level: int, stats: Dict[str, int]) -> int:
    primary = {
        "Warrior": ["might"],
        "Rogue": ["agility"],
        "Cleric": ["spirit"],
        "Mage": ["mind"],
    }.get(hero_class, [])

    secondary = {
        "Warrior": ["spirit"],
        "Rogue": ["mind"],
        "Cleric": ["mind"],
        "Mage": ["spirit"],
    }.get(hero_class, [])

    primary_power = sum(int(stats.get(stat, 0)) * 2 for stat in primary)
    secondary_power = sum(int(stats.get(stat, 0)) for stat in secondary)
    general_power = sum(int(value) for value in stats.values())

    return max(1, primary_power + secondary_power + general_power + (int(level) * 3))


def calculate_contract_values(
    hero_class: str,
    age: int,
    level: int,
    stats: Dict[str, int],
    contract_attitude: str,
    reputation,
    pricing_rules: Dict,
    attitude_multiplier_func,
    injured: bool = False,
) -> tuple[int, int]:
    power = base_combat_power(hero_class, level, stats)

    signing_fee = float(pricing_rules.get("signing_base", 25))
    signing_fee += power * float(pricing_rules.get("signing_power_multiplier", 2.2))
    signing_fee += int(level) * float(pricing_rules.get("signing_level_multiplier", 35))

    wage = float(pricing_rules.get("wage_base", 6))
    wage += power * float(pricing_rules.get("wage_power_multiplier", 0.35))
    wage += int(level) * float(pricing_rules.get("wage_level_multiplier", 5))

    if int(age) <= int(pricing_rules.get("young_premium_age", 24)):
        young_premium = float(pricing_rules.get("young_premium", 1.10))
        signing_fee *= young_premium
        wage *= young_premium

    if int(age) >= int(pricing_rules.get("old_discount_age", 55)):
        old_discount = float(pricing_rules.get("old_discount", 0.80))
        signing_fee *= old_discount
        wage *= old_discount

    if injured:
        injury_discount = float(pricing_rules.get("injury_discount", 0.70))
        signing_fee *= injury_discount
        wage *= injury_discount

    signing_fee *= float(attitude_multiplier_func(contract_attitude, "signing_bonus", reputation))
    wage *= float(attitude_multiplier_func(contract_attitude, "wage", reputation))

    return max(1, int(signing_fee)), max(1, int(wage))


def apply_reputation_to_contract(hero, reputation) -> None:
    def reputation_multiplier(score: int, positive_discount: float, negative_markup: float) -> float:
        if score > 0:
            return max(0.70, 1.0 - ((score / 100.0) * positive_discount))

        if score < 0:
            return min(1.75, 1.0 + ((abs(score) / 100.0) * negative_markup))

        return 1.0

    class_key = str(hero.hero_class).lower()
    class_score = int(getattr(reputation, class_key, 0))

    wage_multiplier = 1.0
    signing_multiplier = 1.0

    wage_multiplier *= reputation_multiplier(
        int(getattr(reputation, "reliability", 0)),
        positive_discount=0.15,
        negative_markup=0.45,
    )
    wage_multiplier *= reputation_multiplier(
        class_score,
        positive_discount=0.12,
        negative_markup=0.25,
    )

    signing_multiplier *= reputation_multiplier(
        int(getattr(reputation, "safety", 0)),
        positive_discount=0.10,
        negative_markup=0.35,
    )
    signing_multiplier *= reputation_multiplier(
        int(getattr(reputation, "overall", 0)),
        positive_discount=0.08,
        negative_markup=0.20,
    )
    signing_multiplier *= reputation_multiplier(
        class_score,
        positive_discount=0.10,
        negative_markup=0.20,
    )

    hero.wage_per_year = max(1, int(hero.wage_per_year * wage_multiplier))
    hero.signing_bonus = max(1, int(hero.signing_bonus * signing_multiplier))