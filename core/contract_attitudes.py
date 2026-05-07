import random
from typing import Dict


DEFAULT_CONTRACT_ATTITUDE = "Practical"


CONTRACT_ATTITUDE_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    "Modest": {
        "signing_bonus": 0.85,
        "wage": 0.85,
    },
    "Practical": {
        "signing_bonus": 1.00,
        "wage": 1.00,
    },
    "Ambitious": {
        "signing_bonus": 1.15,
        "wage": 1.20,
    },
    "Mercenary": {
        "signing_bonus": 1.35,
        "wage": 1.45,
    },
    "Noble": {
        "signing_bonus": 0.95,
        "wage": 0.90,
    },
}


CONTRACT_ATTITUDE_DESCRIPTIONS: Dict[str, str] = {
    "Modest": "Accepts lower pay and values opportunity.",
    "Practical": "Negotiates around market value.",
    "Ambitious": "Expects above-market pay and believes they deserve investment.",
    "Mercenary": "Follows gold first and demands premium contracts.",
    "Noble": "May accept less from a respected and honorable guild.",
}


CONTRACT_ATTITUDE_WEIGHTS: Dict[str, int] = {
    "Modest": 20,
    "Practical": 42,
    "Ambitious": 20,
    "Mercenary": 12,
    "Noble": 6,
}


def random_contract_attitude() -> str:
    attitudes = list(CONTRACT_ATTITUDE_WEIGHTS.keys())
    weights = list(CONTRACT_ATTITUDE_WEIGHTS.values())
    return random.choices(attitudes, weights=weights, k=1)[0]


def attitude_description(contract_attitude: str) -> str:
    return CONTRACT_ATTITUDE_DESCRIPTIONS.get(
        contract_attitude,
        "Unknown contract attitude.",
    )


def goodwill_score(reputation) -> float:
    if reputation is None:
        return 0.0

    overall = float(getattr(reputation, "overall", 0))
    safety = float(getattr(reputation, "safety", 0))
    reliability = float(getattr(reputation, "reliability", 0))

    return (overall + safety + reliability) / 3.0


def attitude_multiplier(contract_attitude: str, field: str, reputation=None) -> float:
    multipliers = CONTRACT_ATTITUDE_MULTIPLIERS.get(
        contract_attitude,
        CONTRACT_ATTITUDE_MULTIPLIERS[DEFAULT_CONTRACT_ATTITUDE],
    )
    multiplier = float(multipliers.get(field, 1.0))

    if contract_attitude == "Noble":
        goodwill = goodwill_score(reputation)

        if goodwill >= 25:
            multiplier *= 0.85
        elif goodwill <= -25:
            multiplier *= 1.20

    return max(0.50, multiplier)