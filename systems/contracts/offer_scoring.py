from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

from systems.guild.rival_guilds import (
    ensure_rival_guild_state,
    rival_guilds,
    rival_interest_reason,
)
from systems.progression.hero_career import career_phase_name

from .market_state import (
    default_offer_for_hero,
    ensure_contract_state,
    ensure_hero_profile,
    get_offer_for_hero,
    get_renewal_offer_for_hero,
)


GRADE_ORDER = ["A", "B", "C", "D", "F"]


def class_reputation_score(state, hero) -> int:
    class_key_map = {
        "Warrior": "warrior",
        "Rogue": "rogue",
        "Cleric": "cleric",
        "Mage": "mage",
    }
    key = class_key_map.get(getattr(hero, "hero_class", ""), "")
    if not key:
        return 0
    return int(getattr(state.reputation, key, 0))


def phase_signing_multiplier(hero) -> float:
    phase = career_phase_name(hero)

    if phase == "Rookie":
        return 0.82
    if phase == "Rising":
        return 0.95
    if phase == "Prime":
        return 1.15
    if phase == "Veteran":
        return 0.96
    if phase == "Elder":
        return 0.82

    return 1.0


def phase_term_preference(hero) -> int:
    phase = career_phase_name(hero)

    if phase == "Rookie":
        return 4
    if phase == "Rising":
        return 3
    if phase == "Prime":
        return 3
    if phase == "Veteran":
        return 2
    if phase == "Elder":
        return 1

    return 3


def tier_score_bonus(hero) -> float:
    tier = getattr(hero, "market_tier", "Standard")
    return {
        "Developmental": -8.0,
        "Standard": 0.0,
        "Premium": 8.0,
        "Elite": 14.0,
    }.get(tier, 0.0)


def renewal_loyalty_modifier(hero) -> float:
    satisfaction = int(getattr(hero, "satisfaction", 50))
    if satisfaction >= 85:
        return 0.80
    if satisfaction >= 70:
        return 0.90
    if satisfaction <= 25:
        return 1.25
    if satisfaction <= 40:
        return 1.12
    return 1.0


def renewal_term_preference(hero) -> int:
    preferred = max(1, int(getattr(hero, "preferred_campaigns", 3)))
    attitude = getattr(hero, "contract_attitude", "Practical")
    phase = career_phase_name(hero)
    phase_preference = phase_term_preference(hero)

    preferred = min(preferred, max(1, phase_preference))

    if phase == "Elder":
        preferred = 1
    elif phase == "Veteran":
        preferred = min(preferred, 2)
    elif phase == "Rookie":
        preferred = max(preferred, 3)

    if attitude == "Mercenary":
        preferred = max(1, preferred - 1)
    elif attitude in ("Practical", "Modest"):
        preferred = max(preferred, 2 if phase != "Elder" else 1)
    elif attitude in ("Ambitious", "Noble"):
        if phase in ("Rookie", "Rising", "Prime"):
            preferred = max(preferred, 3)
        else:
            preferred = min(preferred, 2)

    return max(1, preferred)


def renewal_ask_for_hero(state, hero) -> Tuple[int, int]:
    ensure_hero_profile(hero)

    campaigns = renewal_term_preference(hero)
    signing_fee = max(25, int(hero.asking_signing_fee))

    overall_rep = int(getattr(state.reputation, "overall", 0))
    class_rep = int(class_reputation_score(state, hero))
    phase = career_phase_name(hero)

    signing_fee = int(signing_fee * renewal_loyalty_modifier(hero))

    if overall_rep >= 35:
        signing_fee = int(signing_fee * 0.95)
    elif overall_rep <= -35:
        signing_fee = int(signing_fee * 1.08)

    if class_rep >= 35:
        signing_fee = int(signing_fee * 0.95)
    elif class_rep <= -35:
        signing_fee = int(signing_fee * 1.08)

    if phase == "Rookie":
        signing_fee = int(signing_fee * 0.92)
    elif phase == "Rising":
        signing_fee = int(signing_fee * 0.98)
    elif phase == "Prime":
        signing_fee = int(signing_fee * 1.05)
    elif phase == "Veteran":
        signing_fee = int(signing_fee * 0.94)
    elif phase == "Elder":
        signing_fee = int(signing_fee * 0.82)

    return max(1, campaigns), max(25, signing_fee)


def default_renewal_offer_for_hero(state, hero) -> Dict:
    campaigns, signing_fee = renewal_ask_for_hero(state, hero)
    return {
        "hero_name": hero.name,
        "offered_campaigns": int(campaigns),
        "offered_signing_fee": int(signing_fee),
    }


def grade_for_score(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def grade_range_for_score(score: float, spread: float = 6.0) -> str:
    high = grade_for_score(score + spread)
    low = grade_for_score(score - spread)

    if high == low:
        return high

    high_index = GRADE_ORDER.index(high)
    low_index = GRADE_ORDER.index(low)

    if high_index <= low_index:
        return f"{high}-{low}"
    return f"{low}-{high}"


def mentorship_bonus(state, hero) -> float:
    mentors = []

    for roster_hero in state.roster:
        mentor_value_fn = getattr(roster_hero, "mentorship_value", None)
        mentor_value = int(mentor_value_fn()) if callable(mentor_value_fn) else 0
        if mentor_value <= 0:
            continue

        if roster_hero.hero_class == hero.hero_class:
            mentor_value += 1

        mentors.append(mentor_value)

    if not mentors:
        return 0.0

    return min(10.0, max(mentors) * 2.0)


def offer_score_components(state, hero, campaigns: int, signing_fee: int) -> Dict[str, float]:
    ensure_hero_profile(hero)

    offered_fee_per_campaign = signing_fee / max(1, campaigns)
    asking_fee_per_campaign = max(10.0, float(hero.asking_fee_per_campaign))

    money_delta = (offered_fee_per_campaign - asking_fee_per_campaign) / asking_fee_per_campaign
    money_component = max(-35.0, min(35.0, money_delta * 65.0)) * float(hero.money_per_campaign_weight)

    preferred_campaigns = max(1, int(hero.preferred_campaigns))
    phase_preference = phase_term_preference(hero)
    ideal_campaigns = max(1, min(preferred_campaigns, phase_preference))

    campaign_gap = abs(campaigns - ideal_campaigns)
    term_component = max(-10.0, 8.0 - (campaign_gap * 4.5)) * float(hero.term_weight)

    overall_rep = int(getattr(state.reputation, "overall", 0))
    reliability = int(getattr(state.reputation, "reliability", 0))
    safety = int(getattr(state.reputation, "safety", 0))
    development = int(getattr(state.reputation, "development", 0))
    class_rep = class_reputation_score(state, hero)

    rep_average = (overall_rep + reliability + class_rep) / 3.0
    reputation_component = max(-8.0, min(8.0, rep_average / 10.0)) * float(hero.reputation_weight)
    safety_component = max(-6.0, min(6.0, safety / 12.0)) * float(hero.safety_weight)

    development_source = development
    phase = career_phase_name(hero)
    if phase == "Rookie" or getattr(hero, "is_developmental", False):
        development_source += 12
    elif phase == "Rising":
        development_source += 6
    elif phase == "Elder":
        development_source -= 4

    development_component = max(-6.0, min(8.0, development_source / 10.0)) * float(hero.development_weight)
    mentorship_component = mentorship_bonus(state, hero) * float(hero.mentorship_weight)

    phase_component = 0.0
    if phase == "Rookie":
        phase_component -= 3.0
    elif phase == "Rising":
        phase_component += 2.0
    elif phase == "Prime":
        phase_component += 6.0
    elif phase == "Veteran":
        phase_component += 1.0
    elif phase == "Elder":
        phase_component -= 2.0

    tier_component = tier_score_bonus(hero)

    return {
        "money_per_campaign": money_component,
        "term": term_component,
        "reputation": reputation_component,
        "safety": safety_component,
        "development": development_component,
        "mentorship": mentorship_component,
        "phase": phase_component,
        "tier": tier_component,
    }


def evaluate_offer_score(state, hero, campaigns: int, signing_fee: int) -> float:
    components = offer_score_components(state, hero, campaigns, signing_fee)
    score = 50.0 + sum(components.values())
    return max(0.0, min(100.0, score))


def renewal_relationship_bonus(state, hero) -> float:
    bonus = 0.0
    satisfaction = int(getattr(hero, "satisfaction", 50))

    if satisfaction >= 85:
        bonus += 14.0
    elif satisfaction >= 70:
        bonus += 8.0
    elif satisfaction <= 25:
        bonus -= 12.0
    elif satisfaction <= 40:
        bonus -= 6.0

    bonus += max(-4.0, min(4.0, int(getattr(state.reputation, "overall", 0)) / 20.0))
    bonus += max(-4.0, min(4.0, class_reputation_score(state, hero) / 20.0))

    return bonus


def evaluate_renewal_offer_score(state, hero, campaigns: int, signing_fee: int) -> float:
    base = evaluate_offer_score(state, hero, campaigns, signing_fee)
    return max(0.0, min(100.0, base + renewal_relationship_bonus(state, hero)))


def renewal_acceptance_threshold(state, hero) -> float:
    ask_campaigns, ask_fee = renewal_ask_for_hero(state, hero)
    return max(40.0, evaluate_renewal_offer_score(state, hero, ask_campaigns, ask_fee) - 2.0)


def estimate_player_offer_grade(state, hero, campaigns: int, signing_fee: int) -> str:
    return grade_for_score(evaluate_offer_score(state, hero, campaigns, signing_fee))


def estimate_player_renewal_grade(state, hero, campaigns: int, signing_fee: int) -> str:
    return grade_for_score(evaluate_renewal_offer_score(state, hero, campaigns, signing_fee))


def renewal_risk_label(state, hero, campaigns: int, signing_fee: int) -> str:
    score = evaluate_renewal_offer_score(state, hero, campaigns, signing_fee)
    threshold = renewal_acceptance_threshold(state, hero)

    if score >= threshold + 10:
        return "Low"
    if score >= threshold + 3:
        return "Moderate"
    if score >= threshold:
        return "High"
    return "Very High"


def rival_guild_for_hero(state, hero) -> Optional[Dict]:
    ensure_hero_profile(hero)
    ensure_rival_guild_state(state)

    seed = f"rival:{hero.name}:{getattr(state, 'contract_round', 1)}:{state.year}"
    rng = random.Random(seed)
    guild_pool = rival_guilds(state)

    if not guild_pool:
        return None

    weights = []
    phase = career_phase_name(hero)

    for guild in guild_pool:
        weight = 10 + int(guild.get("aggression", 0)) + max(0, int(guild.get("wealth_bias", 0)))

        if guild.get("class_preference") == hero.hero_class:
            weight += 12

        if getattr(hero, "is_developmental", False):
            weight += max(0, int(guild.get("rookie_interest", 0)))
        else:
            weight += max(0, int(guild.get("prestige", 0)) // 2)

        tier = getattr(hero, "market_tier", "Standard")
        if tier == "Elite":
            weight += max(0, int(guild.get("prestige", 0))) + 8
        elif tier == "Premium":
            weight += max(0, int(guild.get("prestige", 0)) // 2) + 4

        if phase == "Prime":
            weight += 5
        elif phase == "Veteran":
            weight += 2
        elif phase == "Elder":
            weight -= 2

        weights.append(max(1, weight))

    return rng.choices(guild_pool, weights=weights, k=1)[0]


def rival_guild_name_for_hero(state, hero) -> str:
    guild = rival_guild_for_hero(state, hero)
    return guild["name"] if guild is not None else "Unknown Rival"


def rival_summary_for_hero(state, hero) -> Dict[str, str]:
    guild = rival_guild_for_hero(state, hero)
    if guild is None:
        return {
            "name": "Unknown Rival",
            "style": "Unknown",
            "tagline": "",
            "reason": "No clear rival signal",
        }

    return {
        "name": guild["name"],
        "style": guild.get("style", "Unknown"),
        "tagline": guild.get("tagline", ""),
        "reason": rival_interest_reason(guild, hero),
    }


def estimate_rival_offer_score(state, hero) -> Optional[float]:
    ensure_contract_state(state)
    ensure_hero_profile(hero)

    if getattr(state, "market_fallback_open", False) or getattr(state, "market_closed", False):
        return None

    guild = rival_guild_for_hero(state, hero)
    if guild is None:
        return None

    phase = career_phase_name(hero)
    tier = getattr(hero, "market_tier", "Standard")
    combat_power_fn = getattr(hero, "combat_power", None)
    power = int(combat_power_fn()) if callable(combat_power_fn) else int(getattr(hero, "level", 1) * 10)

    tier_bonus = {
        "Developmental": -18,
        "Standard": 0,
        "Premium": 14,
        "Elite": 24,
    }.get(tier, 0)

    phase_bonus = {
        "Rookie": -6,
        "Rising": 4,
        "Prime": 12,
        "Veteran": 5,
        "Elder": -2,
    }.get(phase, 0)

    power_bonus = 0
    if power >= 140:
        power_bonus = 22
    elif power >= 120:
        power_bonus = 16
    elif power >= 100:
        power_bonus = 10
    elif power >= 85:
        power_bonus = 5

    subclass_bonus = min(10, len(getattr(hero, "unlocked_subclasses", []) or []) * 4)

    seed = (
        f"{guild['name']}:{hero.name}:{getattr(state, 'contract_round', 1)}:"
        f"{state.year}:{getattr(state, 'market_stage', 1)}"
    )
    rng = random.Random(seed)

    interest = 0.10

    if tier == "Elite":
        interest = 0.96
    elif tier == "Premium":
        interest = 0.82
    elif phase == "Prime":
        interest = 0.72
    elif phase == "Veteran":
        interest = 0.54
    elif getattr(hero, "is_developmental", False):
        interest = 0.28
    elif phase == "Rookie":
        interest = 0.18

    if power >= 120:
        interest += 0.16
    elif power >= 100:
        interest += 0.10
    elif power >= 85:
        interest += 0.06
    elif power <= 55:
        interest -= 0.12

    if guild.get("class_preference") == hero.hero_class:
        interest += 0.12

    if getattr(hero, "is_developmental", False):
        interest += max(0, int(guild.get("rookie_interest", 0))) / 140.0
    else:
        interest += max(0, int(guild.get("aggression", 0))) / 180.0
        interest += max(0, int(guild.get("prestige", 0))) / 220.0

    if phase == "Elder":
        interest -= 0.08

    interest = max(0.02, min(0.99, interest))

    if rng.random() > interest:
        return None

    base = 48.0
    base += tier_bonus
    base += phase_bonus
    base += power_bonus
    base += subclass_bonus
    base += int(guild.get("wealth_bias", 0)) * 0.8
    base += int(guild.get("aggression", 0)) * 0.40
    base += int(guild.get("prestige", 0)) * 0.35

    if guild.get("class_preference") == hero.hero_class:
        base += 10

    if getattr(hero, "is_developmental", False):
        base += int(guild.get("rookie_interest", 0)) * 0.45

    if getattr(hero, "contract_attitude", "") == "Mercenary":
        base += 4
    if getattr(hero, "contract_attitude", "") == "Noble":
        base += 2 + (int(guild.get("prestige", 0)) * 0.20)

    base += rng.randint(-5, 5)

    return max(25.0, min(98.0, base))


def personal_acceptance_threshold(state, hero) -> float:
    ensure_hero_profile(hero)

    phase = career_phase_name(hero)
    tier = getattr(hero, "market_tier", "Standard")
    satisfaction_like = 50.0

    threshold = 54.0

    threshold += {
        "Rookie": -4.0,
        "Rising": 1.0,
        "Prime": 8.0,
        "Veteran": 4.0,
        "Elder": 2.0,
    }.get(phase, 0.0)

    threshold += {
        "Developmental": -6.0,
        "Standard": 0.0,
        "Premium": 5.0,
        "Elite": 10.0,
    }.get(tier, 0.0)

    combat_power_fn = getattr(hero, "combat_power", None)
    power = int(combat_power_fn()) if callable(combat_power_fn) else int(getattr(hero, "level", 1) * 10)

    if power >= 120:
        threshold += 8.0
    elif power >= 100:
        threshold += 5.0
    elif power >= 85:
        threshold += 3.0

    attitude = getattr(hero, "contract_attitude", "Practical")
    if attitude == "Mercenary":
        threshold += 4.0
    elif attitude == "Ambitious":
        threshold += 3.0
    elif attitude == "Noble":
        threshold += 2.0
    elif attitude == "Modest":
        threshold -= 3.0

    if getattr(hero, "is_developmental", False):
        threshold -= 4.0

    threshold += max(-3.0, min(3.0, (50.0 - satisfaction_like) / 20.0))

    return max(38.0, min(82.0, threshold))


def estimate_rival_grade_hint(state, hero) -> str:
    rival_score = estimate_rival_offer_score(state, hero)
    if rival_score is None:
        return "N/A"
    return grade_range_for_score(rival_score)


def visible_offer_modifiers(state, hero, campaigns: int, signing_fee: int) -> List[str]:
    components = offer_score_components(state, hero, campaigns, signing_fee)
    lines: List[str] = []

    if components["money_per_campaign"] >= 7:
        lines.append("+ Strong pay per campaign")
    elif components["money_per_campaign"] <= -7:
        lines.append("- Pay per campaign too low")

    if components["term"] >= 2:
        lines.append("+ Contract length fits")
    elif components["term"] <= -2:
        lines.append("- Contract length mismatch")

    if components["mentorship"] >= 1:
        lines.append("+ Strong mentorship available")

    if components["reputation"] >= 1.5:
        lines.append("+ Guild reputation helps")
    elif components["reputation"] <= -1.5:
        lines.append("- Guild reputation hurts")

    if components["safety"] >= 1:
        lines.append("+ Guild feels safer")
    elif components["safety"] <= -1:
        lines.append("- Guild feels risky")

    if components["development"] >= 1:
        lines.append("+ Good development path")

    if components["phase"] >= 5:
        lines.append("+ Proven in prime years")
    elif components["phase"] <= -2:
        lines.append("- Phase reduces urgency")

    if components["tier"] >= 8:
        lines.append("+ High market status")

    if not lines:
        lines.append("No major visible modifiers")

    return lines[:4]


def visible_renewal_modifiers(state, hero, campaigns: int, signing_fee: int) -> List[str]:
    lines = visible_offer_modifiers(state, hero, campaigns, signing_fee)

    satisfaction = int(getattr(hero, "satisfaction", 50))
    if satisfaction >= 75:
        lines.append("+ Loyalty discount")
    elif satisfaction <= 35:
        lines.append("- Frustration penalty")

    if class_reputation_score(state, hero) >= 25:
        lines.append("+ Familiar class reputation")
    elif class_reputation_score(state, hero) <= -25:
        lines.append("- Distrusts guild direction")

    if getattr(state.reputation, "overall", 0) >= 25:
        lines.append("+ Stable guild environment")

    deduped = []
    for line in lines:
        if line not in deduped:
            deduped.append(line)

    return deduped[:4]


def round_offer_summary(state, hero) -> Tuple[int, int]:
    offer = get_offer_for_hero(state, hero)
    if offer is None:
        default_offer = default_offer_for_hero(hero)
        return default_offer["offered_campaigns"], default_offer["offered_signing_fee"]

    return int(offer["offered_campaigns"]), int(offer["offered_signing_fee"])


def renewal_offer_summary(state, hero) -> Tuple[int, int]:
    offer = get_renewal_offer_for_hero(state, hero)
    if offer is None:
        default_offer = default_renewal_offer_for_hero(state, hero)
        return default_offer["offered_campaigns"], default_offer["offered_signing_fee"]

    return int(offer["offered_campaigns"]), int(offer["offered_signing_fee"])