import random
from typing import Dict, List, Optional, Tuple

from hero_generator import generate_fallback_contract_market
from manager_reputation import CLASS_REPUTATION_KEYS
from systems.hero_career import career_phase_name
from systems.rival_guilds import (
    add_hero_to_rival_guild,
    add_market_history_entry,
    ensure_rival_guild_state,
    rival_guilds,
    rival_interest_reason,
)


GRADE_ORDER = ["A", "B", "C", "D", "F"]
FALLBACK_CONTRACT_CAMPAIGNS = 1

def ensure_contract_state(state) -> None:
    if not hasattr(state, "contract_offers"):
        state.contract_offers = []

    if not hasattr(state, "renewal_offers"):
        state.renewal_offers = []

    if not hasattr(state, "contract_round"):
        state.contract_round = 1

    if not hasattr(state, "seasonal_contract_pool"):
        state.seasonal_contract_pool = list(getattr(state, "available_contracts", []))

    if not hasattr(state, "market_stage"):
        state.market_stage = 1

    if not hasattr(state, "market_stage_max"):
        state.market_stage_max = 3

    if not hasattr(state, "market_cycle"):
        state.market_cycle = 1

    if not hasattr(state, "market_fallback_open"):
        state.market_fallback_open = False

    if not hasattr(state, "market_closed"):
        state.market_closed = False

    ensure_rival_guild_state(state)
    

def ensure_hero_profile(hero) -> None:
    if not hasattr(hero, "preferred_campaigns"):
        hero.preferred_campaigns = max(1, getattr(hero, "contract_years", 3))

    if not hasattr(hero, "asking_signing_fee"):
        hero.asking_signing_fee = max(25, getattr(hero, "signing_bonus", 100))

    if not hasattr(hero, "asking_fee_per_campaign"):
        hero.asking_fee_per_campaign = max(
            10,
            int(round(hero.asking_signing_fee / max(1, hero.preferred_campaigns))),
        )

    for attr, default in [
        ("money_per_campaign_weight", 0.70),
        ("term_weight", 0.10),
        ("mentorship_weight", 0.05),
        ("reputation_weight", 0.06),
        ("safety_weight", 0.03),
        ("development_weight", 0.06),
        ("market_tier", "Standard"),
        ("is_developmental", False),
    ]:
        if not hasattr(hero, attr):
            setattr(hero, attr, default)

def market_stage_label(state) -> str:
    ensure_contract_state(state)

    if getattr(state, "market_closed", False):
        return "Closed"

    if getattr(state, "market_fallback_open", False):
        return "Fallback"

    return f"Stage {int(getattr(state, 'market_stage', 1))}/{int(getattr(state, 'market_stage_max', 3))}"


def fallback_static_price(hero) -> int:
    ensure_hero_profile(hero)

    price = int(getattr(hero, "asking_signing_fee", 100) * 0.55)

    tier = getattr(hero, "market_tier", "Standard")
    if tier == "Developmental":
        price = int(price * 0.85)
    elif tier == "Premium":
        price = int(price * 1.10)
    elif tier == "Elite":
        price = int(price * 1.20)

    phase = career_phase_name(hero)
    if phase == "Rookie":
        price = int(price * 0.90)
    elif phase == "Prime":
        price = int(price * 1.05)
    elif phase == "Veteran":
        price = int(price * 0.90)
    elif phase == "Elder":
        price = int(price * 0.80)

    return max(25, price)


def convert_hero_to_fallback_contract(hero) -> None:
    ensure_hero_profile(hero)
    hero.preferred_campaigns = FALLBACK_CONTRACT_CAMPAIGNS
    hero.asking_signing_fee = fallback_static_price(hero)
    hero.asking_fee_per_campaign = hero.asking_signing_fee


def open_fallback_market(state, heroes: List) -> None:
    ensure_contract_state(state)

    remaining = list(heroes)
    for hero in remaining:
        convert_hero_to_fallback_contract(hero)

    state.market_fallback_open = True
    state.market_closed = False
    state.available_contracts = remaining
    state.seasonal_contract_pool = list(remaining)
    state.contract_offers = []

    state.market_history.append(
        f"Fallback market opened with {len(remaining)} unsigned hero(es) at fixed 1-campaign prices."
    )


def close_market_cycle(state) -> List[str]:
    ensure_contract_state(state)

    results = []
    unsigned = list(getattr(state, "available_contracts", []))

    if unsigned:
        state.retired_heroes.extend(unsigned)
        results.append(f"{len(unsigned)} unsigned hero(es) left the market and are out of circulation.")

    state.available_contracts = []
    state.seasonal_contract_pool = []
    state.contract_offers = []
    state.market_fallback_open = False
    state.market_closed = True
    state.contract_round = 1
    state.market_stage = 1

    return results

def is_expiring_hero(hero) -> bool:
    return max(0, int(getattr(hero, "contract_years", 0))) <= 1


def get_offer_for_hero(state, hero) -> Optional[Dict]:
    ensure_contract_state(state)

    for offer in state.contract_offers:
        if offer["hero_name"] == hero.name:
            return offer

    return None


def get_renewal_offer_for_hero(state, hero) -> Optional[Dict]:
    ensure_contract_state(state)

    for offer in state.renewal_offers:
        if offer["hero_name"] == hero.name:
            return offer

    return None


def class_reputation_score(state, hero) -> int:
    key = CLASS_REPUTATION_KEYS.get(hero.hero_class)
    if not key:
        return 0
    return getattr(state.reputation, key, 0)


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


def default_offer_for_hero(hero) -> Dict:
    ensure_hero_profile(hero)

    campaigns = max(1, int(getattr(hero, "preferred_campaigns", 3)))
    signing_fee = max(25, int(getattr(hero, "asking_signing_fee", 100)))

    return {
        "hero_name": hero.name,
        "offered_campaigns": campaigns,
        "offered_signing_fee": signing_fee,
    }


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

def queue_offer(state, hero, campaigns: int, signing_fee: int) -> None:
    ensure_contract_state(state)
    ensure_hero_profile(hero)

    if getattr(state, "market_fallback_open", False):
        campaigns = FALLBACK_CONTRACT_CAMPAIGNS
        signing_fee = fallback_static_price(hero)
    else:
        campaigns = max(1, int(campaigns))
        signing_fee = max(25, int(signing_fee))

    existing = get_offer_for_hero(state, hero)
    if existing is not None:
        existing["offered_campaigns"] = campaigns
        existing["offered_signing_fee"] = signing_fee
        return

    state.contract_offers.append(
        {
            "hero_name": hero.name,
            "offered_campaigns": campaigns,
            "offered_signing_fee": signing_fee,
        }
    )

def queue_renewal_offer(state, hero, campaigns: int, signing_fee: int) -> None:
    ensure_contract_state(state)
    ensure_hero_profile(hero)

    campaigns = max(1, int(campaigns))
    signing_fee = max(25, int(signing_fee))

    existing = get_renewal_offer_for_hero(state, hero)
    if existing is not None:
        existing["offered_campaigns"] = campaigns
        existing["offered_signing_fee"] = signing_fee
        return

    state.renewal_offers.append(
        {
            "hero_name": hero.name,
            "offered_campaigns": campaigns,
            "offered_signing_fee": signing_fee,
        }
    )


def clear_offer(state, hero) -> None:
    ensure_contract_state(state)
    state.contract_offers = [
        offer
        for offer in state.contract_offers
        if offer["hero_name"] != hero.name
    ]


def clear_renewal_offer(state, hero) -> None:
    ensure_contract_state(state)
    state.renewal_offers = [
        offer
        for offer in state.renewal_offers
        if offer["hero_name"] != hero.name
    ]


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
        mentor_value = getattr(roster_hero, "mentorship_value", lambda: 0)()
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

    overall_rep = getattr(state.reputation, "overall", 0)
    reliability = getattr(state.reputation, "reliability", 0)
    safety = getattr(state.reputation, "safety", 0)
    development = getattr(state.reputation, "development", 0)
    class_rep = class_reputation_score(state, hero)

    rep_average = (overall_rep + reliability + class_rep) / 3.0
    reputation_component = max(-8.0, min(8.0, rep_average / 10.0)) * float(hero.reputation_weight)
    safety_component = max(-6.0, min(6.0, safety / 12.0)) * float(hero.safety_weight)

    development_source = development
    if career_phase_name(hero) == "Rookie" or getattr(hero, "is_developmental", False):
        development_source += 12
    elif career_phase_name(hero) == "Rising":
        development_source += 6
    elif career_phase_name(hero) == "Elder":
        development_source -= 4

    development_component = max(-6.0, min(8.0, development_source / 10.0)) * float(hero.development_weight)
    mentorship_component = mentorship_bonus(state, hero) * float(hero.mentorship_weight)

    phase_component = 0.0
    phase = career_phase_name(hero)
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

    bonus += max(-4.0, min(4.0, getattr(state.reputation, "overall", 0) / 20.0))
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
        weight = 10 + guild.get("aggression", 0) + max(0, guild.get("wealth_bias", 0))

        if guild.get("class_preference") == hero.hero_class:
            weight += 12

        if getattr(hero, "is_developmental", False):
            weight += max(0, guild.get("rookie_interest", 0))
        else:
            weight += max(0, guild.get("prestige", 0) // 2)

        tier = getattr(hero, "market_tier", "Standard")
        if tier == "Elite":
            weight += max(0, guild.get("prestige", 0)) + 8
        elif tier == "Premium":
            weight += max(0, guild.get("prestige", 0) // 2) + 4

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
    power = int(hero.combat_power()) if hasattr(hero, "combat_power") else int(getattr(hero, "level", 1) * 10)

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

    seed = f"{guild['name']}:{hero.name}:{getattr(state, 'contract_round', 1)}:{state.year}:{getattr(state, 'market_stage', 1)}"
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
        interest += max(0, guild.get("rookie_interest", 0)) / 140.0
    else:
        interest += max(0, guild.get("aggression", 0)) / 180.0
        interest += max(0, guild.get("prestige", 0)) / 220.0

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
    base += guild.get("wealth_bias", 0) * 0.8
    base += guild.get("aggression", 0) * 0.40
    base += guild.get("prestige", 0) * 0.35

    if guild.get("class_preference") == hero.hero_class:
        base += 10

    if getattr(hero, "is_developmental", False):
        base += guild.get("rookie_interest", 0) * 0.45

    if getattr(hero, "contract_attitude", "") == "Mercenary":
        base += 4
    if getattr(hero, "contract_attitude", "") == "Noble":
        base += 2 + (guild.get("prestige", 0) * 0.20)

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

    power = int(getattr(hero, "combat_power", lambda: 0)()) if callable(getattr(hero, "combat_power", None)) else int(getattr(hero, "level", 1) * 10)
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

    return offer["offered_campaigns"], offer["offered_signing_fee"]


def renewal_offer_summary(state, hero) -> Tuple[int, int]:
    offer = get_renewal_offer_for_hero(state, hero)
    if offer is None:
        default_offer = default_renewal_offer_for_hero(state, hero)
        return default_offer["offered_campaigns"], default_offer["offered_signing_fee"]

    return offer["offered_campaigns"], offer["offered_signing_fee"]



def resolve_contract_round(state) -> List[str]:
    ensure_contract_state(state)

    results: List[str] = []

    if getattr(state, "market_closed", False):
        results.append("The hiring market is closed until the next cycle.")
        return results

    if getattr(state, "market_fallback_open", False):
        close_messages = close_market_cycle(state)
        for message in close_messages:
            results.append(message)
            add_market_history_entry(state, message)

        if not close_messages:
            message = "Fallback hiring ended."
            results.append(message)
            add_market_history_entry(state, message)

        return results

    stage_text = market_stage_label(state)
    header = f"=== Hiring {stage_text} ==="
    results.append(header)
    add_market_history_entry(state, header)

    offers_by_name = {
        offer["hero_name"]: offer
        for offer in state.contract_offers
    }

    roster_capacity = getattr(state.guild_upgrades, "roster_capacity", len(state.roster))
    open_slots = max(0, roster_capacity - len(state.roster))
    remaining_gold = state.gold

    current_market = list(state.available_contracts)

    signed_to_player = []
    signed_elsewhere = []
    rejected_offers = []
    processed_names = set()
    persistent_offer_names = set()

    offered_heroes = [
        hero
        for hero in current_market
        if hero.name in offers_by_name
    ]
    offered_heroes.sort(
        key=lambda hero: evaluate_offer_score(
            state,
            hero,
            offers_by_name[hero.name]["offered_campaigns"],
            offers_by_name[hero.name]["offered_signing_fee"],
        ),
        reverse=True,
    )

    for hero in offered_heroes:
        processed_names.add(hero.name)
        offer = offers_by_name[hero.name]

        campaigns = int(offer["offered_campaigns"])
        signing_fee = int(offer["offered_signing_fee"])

        player_score = evaluate_offer_score(state, hero, campaigns, signing_fee)
        rival_score = estimate_rival_offer_score(state, hero)
        rival_name = rival_guild_name_for_hero(state, hero)
        accept_threshold = personal_acceptance_threshold(state, hero)

        if open_slots <= 0:
            message = f"{hero.name}: no roster space remained, so the offer failed."
            results.append(message)
            add_market_history_entry(state, message)
            persistent_offer_names.add(hero.name)
            continue

        if remaining_gold < signing_fee:
            message = f"{hero.name}: not enough gold remained to honor the offer."
            results.append(message)
            add_market_history_entry(state, message)
            persistent_offer_names.add(hero.name)
            continue

        if player_score < accept_threshold and (rival_score is None or rival_score < accept_threshold):
            rejected_offers.append(hero)
            persistent_offer_names.add(hero.name)
            message = (
                f"{hero.name} rejected all current offers. "
                f"Your offer grade {grade_for_score(player_score)} was below their standard."
            )
            results.append(message)
            add_market_history_entry(state, message)
            continue

        if rival_score is None:
            if player_score >= accept_threshold:
                remaining_gold -= signing_fee
                open_slots -= 1

                hero.contract_years = campaigns
                hero.signing_bonus = signing_fee

                state.roster.append(hero)
                signed_to_player.append(hero)

                message = f"{hero.name} accepted your deal ({signing_fee}g / {campaigns}c)."
                results.append(message)
                add_market_history_entry(state, message)
            else:
                rejected_offers.append(hero)
                persistent_offer_names.add(hero.name)
                message = f"{hero.name} rejected your offer."
                results.append(message)
                add_market_history_entry(state, message)
            continue

        best_score = max(player_score, rival_score)

        if best_score < accept_threshold:
            rejected_offers.append(hero)
            persistent_offer_names.add(hero.name)
            message = (
                f"{hero.name} rejected both your offer and the rival approach. "
                f"They are holding out for better terms."
            )
            results.append(message)
            add_market_history_entry(state, message)
            continue

        if player_score >= rival_score and player_score >= accept_threshold:
            remaining_gold -= signing_fee
            open_slots -= 1

            hero.contract_years = campaigns
            hero.signing_bonus = signing_fee

            state.roster.append(hero)
            signed_to_player.append(hero)

            message = (
                f"{hero.name} accepted your deal ({signing_fee}g / {campaigns}c). "
                f"Your offer {grade_for_score(player_score)} beat rivals {grade_for_score(rival_score)}."
            )
            results.append(message)
            add_market_history_entry(state, message)
        elif rival_score >= accept_threshold:
            signed_elsewhere.append(hero)
            add_hero_to_rival_guild(state, rival_name, hero)

            message = (
                f"{hero.name} signed with {rival_name}. "
                f"Your offer {grade_for_score(player_score)} vs rivals {grade_for_score(rival_score)}."
            )
            results.append(message)
            add_market_history_entry(state, message)
        else:
            rejected_offers.append(hero)
            persistent_offer_names.add(hero.name)
            message = f"{hero.name} rejected the current market and remained unsigned."
            results.append(message)
            add_market_history_entry(state, message)

    for hero in current_market:
        if hero.name in processed_names:
            continue

        rival_score = estimate_rival_offer_score(state, hero)
        rival_name = rival_guild_name_for_hero(state, hero)
        accept_threshold = personal_acceptance_threshold(state, hero)

        if rival_score is not None and rival_score >= accept_threshold:
            signed_elsewhere.append(hero)
            add_hero_to_rival_guild(state, rival_name, hero)

            message = f"{hero.name} signed with {rival_name}."
            results.append(message)
            add_market_history_entry(state, message)
        else:
            message = f"{hero.name} remained unsigned."
            results.append(message)
            add_market_history_entry(state, message)

    state.gold = remaining_gold

    signed_names = {hero.name for hero in signed_to_player}
    rival_names = {hero.name for hero in signed_elsewhere}

    remaining_market = [
        hero
        for hero in current_market
        if hero.name not in signed_names and hero.name not in rival_names
    ]

    state.available_contracts = list(remaining_market)
    state.seasonal_contract_pool = list(remaining_market)

    state.contract_offers = [
        offer
        for offer in state.contract_offers
        if offer["hero_name"] in persistent_offer_names
        and offer["hero_name"] in {hero.name for hero in remaining_market}
    ]

    if signed_to_player:
        message = f"You signed {len(signed_to_player)} hero(es) this stage."
        results.append(message)
        add_market_history_entry(state, message)
    else:
        message = "You did not sign any heroes this stage."
        results.append(message)
        add_market_history_entry(state, message)

    if rejected_offers:
        message = f"{len(rejected_offers)} hero(es) rejected the current terms."
        results.append(message)
        add_market_history_entry(state, message)

    if persistent_offer_names:
        message = f"{len(persistent_offer_names)} offer(s) remain active for the next stage."
        results.append(message)
        add_market_history_entry(state, message)

    if int(getattr(state, "market_stage", 1)) < int(getattr(state, "market_stage_max", 3)):
        state.market_stage += 1
        state.contract_round = state.market_stage

        message = (
            f"Advanced to hiring stage {state.market_stage}/{state.market_stage_max}. "
            f"{len(remaining_market)} recruit(s) remain in the pool."
        )
        results.append(message)
        add_market_history_entry(state, message)
    else:
        open_fallback_market(state, remaining_market)

        message = (
            f"Negotiation stages are complete. "
            f"{len(remaining_market)} recruit(s) moved to fixed 1-campaign fallback deals."
        )
        results.append(message)
        add_market_history_entry(state, message)

    return results
