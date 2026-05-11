"""
core/contract_attitudes.py

Defines the five hero contract attitudes and their effect on negotiation.

Attitude names (updated to match GDD/TDD):
    Humble        — low financial demands, values the opportunity
    Pragmatic     — negotiates around market value (most common)
    Ambitious     — expects above-market investment
    Honorable     — may discount for a guild with strong recent standing
    Opportunistic — follows gold first; premium contracts required

Attitudes also lightly modify how much a hero cares about the guild's
recent standing (RecentReputation.standing) when deciding whether to sign.
The `reputation_sensitivity` value is a weight on standing: a hero with
higher sensitivity receives a slightly larger nudge — positive or negative —
from the guild's recent market perception.

This replaces the old Modest/Practical/Ambitious/Mercenary/Noble set and
the multi-axis goodwill_score() that read from the deprecated 9-axis
ManagerReputation object.
"""

from __future__ import annotations

import random
from typing import Dict


DEFAULT_CONTRACT_ATTITUDE = "Pragmatic"


# Multipliers applied to the hero's baseline asking price.
CONTRACT_ATTITUDE_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    "Humble": {
        "signing_bonus": 0.85,
        "wage": 0.85,
    },
    "Pragmatic": {
        "signing_bonus": 1.00,
        "wage": 1.00,
    },
    "Ambitious": {
        "signing_bonus": 1.15,
        "wage": 1.20,
    },
    "Honorable": {
        "signing_bonus": 0.95,
        "wage": 0.90,
    },
    "Opportunistic": {
        "signing_bonus": 1.35,
        "wage": 1.45,
    },
}


CONTRACT_ATTITUDE_DESCRIPTIONS: Dict[str, str] = {
    "Humble":       "Accepts lower pay and values the chance to prove themselves.",
    "Pragmatic":    "Negotiates around market value without strong feelings either way.",
    "Ambitious":    "Expects above-market pay and believes they deserve real investment.",
    "Honorable":    "May accept less from a guild with a solid recent reputation.",
    "Opportunistic": "Follows gold first and demands premium contracts.",
}


# How strongly each attitude weights the guild's recent standing when
# evaluating an offer.  Honorable heroes care the most; Opportunistic
# heroes care the least (money matters more than reputation to them).
REPUTATION_SENSITIVITY: Dict[str, float] = {
    "Humble":        0.8,
    "Pragmatic":     1.0,
    "Ambitious":     1.1,
    "Honorable":     1.6,
    "Opportunistic": 0.4,
}


# Spawn weights for random generation.
CONTRACT_ATTITUDE_WEIGHTS: Dict[str, int] = {
    "Humble":        20,
    "Pragmatic":     40,
    "Ambitious":     20,
    "Honorable":      8,
    "Opportunistic": 12,
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


def reputation_sensitivity(contract_attitude: str) -> float:
    """
    Returns how strongly a hero with this attitude weights guild standing.
    Used by offer_scoring to scale the standing acceptance modifier.
    """
    return float(REPUTATION_SENSITIVITY.get(contract_attitude, 1.0))


def attitude_multiplier(contract_attitude: str, field: str, reputation=None) -> float:
    """
    Returns the price multiplier for the given attitude and field
    ('signing_bonus' or 'wage').

    For Honorable heroes, the multiplier is slightly reduced when the
    guild's recent standing is positive, and slightly increased when it is
    negative.  The effect is kept very small so that standing never
    dominates the contract outcome — it only softens or hardens the edge.

    `reputation` should be a RecentReputation instance (or None).
    """
    multipliers = CONTRACT_ATTITUDE_MULTIPLIERS.get(
        contract_attitude,
        CONTRACT_ATTITUDE_MULTIPLIERS[DEFAULT_CONTRACT_ATTITUDE],
    )
    multiplier = float(multipliers.get(field, 1.0))

    if contract_attitude == "Honorable" and reputation is not None:
        standing = int(getattr(reputation, "standing", 0))

        if standing >= 2:
            multiplier *= 0.92   # noticeable discount for strong standing
        elif standing == 1:
            multiplier *= 0.96   # slight discount for positive standing
        elif standing == -1:
            multiplier *= 1.06   # slight markup for poor standing
        elif standing <= -2:
            multiplier *= 1.12   # larger markup for troubled standing

    return max(0.50, multiplier)


# ---------------------------------------------------------------------------
# Backward-compatibility shims
# Old code referenced goodwill_score() from this module.  Keep a stub that
# returns 0.0 so nothing hard-crashes during transition; callers should be
# migrated to use RecentReputation.standing directly.
# ---------------------------------------------------------------------------

def goodwill_score(reputation) -> float:  # pragma: no cover
    """
    DEPRECATED.  Use `reputation.standing` (RecentReputation) directly.
    Returns a float approximation so old callers don't crash immediately.
    """
    standing = int(getattr(reputation, "standing", 0))
    return float(standing * 12.5)   # maps [-2,+2] → [-25,+25], old rough range