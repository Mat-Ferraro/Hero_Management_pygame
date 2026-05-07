import random
from typing import Dict


DEFAULT_GROWTH_RATE = "Talented"


GROWTH_RATE_MULTIPLIERS: Dict[str, float] = {
    "Mundane": 0.80,
    "Talented": 1.00,
    "Gifted": 1.20,
    "Heroic": 1.40,
    "Legendary": 1.70,
    "Mythic": 2.00,
}


GROWTH_RATE_DESCRIPTIONS: Dict[str, str] = {
    "Mundane": "Slow learner. Lower long-term development potential.",
    "Talented": "Reliable baseline growth.",
    "Gifted": "Strong natural talent and above-average growth.",
    "Heroic": "Elite growth. Excellent long-term investment.",
    "Legendary": "Rare franchise-defining growth.",
    "Mythic": "Extremely rare world-shaping potential.",
}


GROWTH_RATE_WEIGHTS: Dict[str, int] = {
    "Mundane": 40,
    "Talented": 30,
    "Gifted": 18,
    "Heroic": 8,
    "Legendary": 3,
    "Mythic": 1,
}


def growth_multiplier(growth_rate: str) -> float:
    return float(
        GROWTH_RATE_MULTIPLIERS.get(
            growth_rate,
            GROWTH_RATE_MULTIPLIERS[DEFAULT_GROWTH_RATE],
        )
    )


def growth_description(growth_rate: str) -> str:
    return GROWTH_RATE_DESCRIPTIONS.get(
        growth_rate,
        "Unknown growth potential.",
    )


def random_growth_rate() -> str:
    growth_rates = list(GROWTH_RATE_WEIGHTS.keys())
    weights = list(GROWTH_RATE_WEIGHTS.values())
    return random.choices(growth_rates, weights=weights, k=1)[0]