"""
systems/contracts/hero_contract_valuation.py

Calculates the raw signing fee and wage for a hero, then optionally adjusts
them based on guild standing.

Reputation integration (v11 design):
  The old apply_reputation_to_contract() applied five separate multipliers
  derived from overall, reliability, safety, and class-specific reputation
  axes.  This inflated or deflated wages by up to 75% in extreme cases,
  turning reputation into a large hidden economy.

  The replacement is intentionally smaller.  Guild standing [-2, +2] shifts
  the final asking price by ±5% at the extremes.  This is barely perceptible
  on any single transaction but creates a real cumulative difference over a
  full market cycle.
"""

from __future__ import annotations

from typing import Dict


# ---------------------------------------------------------------------------
# Power calculation
# ---------------------------------------------------------------------------

def base_combat_power(hero_class: str, level: int, stats: Dict[str, int]) -> int:
    primary = {
        "Warrior": ["might"],
        "Rogue":   ["agility"],
        "Cleric":  ["spirit"],
        "Mage":    ["mind"],
    }.get(hero_class, [])

    secondary = {
        "Warrior": ["spirit"],
        "Rogue":   ["mind"],
        "Cleric":  ["mind"],
        "Mage":    ["spirit"],
    }.get(hero_class, [])

    primary_power   = sum(int(stats.get(stat, 0)) * 2 for stat in primary)
    secondary_power = sum(int(stats.get(stat, 0)) for stat in secondary)
    general_power   = sum(int(value) for value in stats.values())

    return max(1, primary_power + secondary_power + general_power + (int(level) * 3))


# ---------------------------------------------------------------------------
# Core valuation
# ---------------------------------------------------------------------------

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
        signing_fee *= float(pricing_rules.get("young_premium", 1.10))
        wage        *= float(pricing_rules.get("young_premium", 1.10))

    if int(age) >= int(pricing_rules.get("old_discount_age", 55)):
        signing_fee *= float(pricing_rules.get("old_discount", 0.80))
        wage        *= float(pricing_rules.get("old_discount", 0.80))

    if injured:
        discount = float(pricing_rules.get("injury_discount", 0.70))
        signing_fee *= discount
        wage        *= discount

    # Attitude multiplier (Honorable heroes check standing inside this call).
    signing_fee *= float(attitude_multiplier_func(contract_attitude, "signing_bonus", reputation))
    wage        *= float(attitude_multiplier_func(contract_attitude, "wage", reputation))

    return max(1, int(signing_fee)), max(1, int(wage))


# ---------------------------------------------------------------------------
# Standing-based price adjustment
# ---------------------------------------------------------------------------

def apply_reputation_to_contract(hero, reputation) -> None:
    """
    Applies a small standing-based adjustment to the hero's asking price.

    Standing [-2, +2] shifts the price by ±2.5% per point (total range
    ±5%).  Positive standing = the market is warm to the guild = slightly
    lower asking price.  Negative standing = the market is cold = slightly
    higher asking price.

    This replaces the old five-multiplier system that could move prices
    by up to 75%.
    """
    standing = int(getattr(reputation, "standing", 0))
    if standing == 0:
        return

    # +0.025 per standing point: standing +2 → multiplier 0.95 (5% cheaper)
    #                            standing -2 → multiplier 1.05 (5% more expensive)
    multiplier = 1.0 - (standing * 0.025)
    multiplier = max(0.90, min(1.10, multiplier))  # hard-cap to ±10% just in case

    hero.wage_per_year  = max(1, int(hero.wage_per_year  * multiplier))
    hero.signing_bonus  = max(1, int(hero.signing_bonus  * multiplier))