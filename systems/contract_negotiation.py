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


def ensure_contract_state(state) -> None:
    if not hasattr(state, "contract_offers"):
        state.contract_offers = []

    if not hasattr(state, "renewal_offers"):
        state.renewal_offers = []

    if not hasattr(state, "contract_round"):
        state.contract_round = 1

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

    guild = rival_guild_for_hero(state, hero)
    if guild is None:
        return None

    tier_bonus = {
        "Developmental": -14,
        "Standard": 0,
        "Premium": 10,
        "Elite": 18,
    }.get(getattr(hero, "market_tier", "Standard"), 0)

    phase_bonus = {
        "Rookie": -4,
        "Rising": 3,
        "Prime": 9,
        "Veteran": 2,
        "Elder": -3,
    }.get(career_phase_name(hero), 0)

    seed = f"{guild['name']}:{hero.name}:{getattr(state, 'contract_round', 1)}:{state.year}"
    rng = random.Random(seed)

    interest_roll = rng.random()
    interest_threshold = 0.15

    if getattr(hero, "is_developmental", False):
        interest_threshold = 0.65 - (max(0, guild.get("rookie_interest", 0)) / 40.0)
    else:
        interest_threshold = 0.15 - (max(0, guild.get("aggression", 0)) / 100.0)

    if career_phase_name(hero) == "Prime":
        interest_threshold -= 0.05
    elif career_phase_name(hero) == "Elder":
        interest_threshold += 0.06

    interest_threshold = max(0.02, min(0.85, interest_threshold))
    if interest_roll < interest_threshold:
        return None

    base = 56.0 + tier_bonus + phase_bonus + rng.randint(-7, 7)
    base += guild.get("wealth_bias", 0) * 0.9
    base += guild.get("aggression", 0) * 0.45
    base += guild.get("prestige", 0) * 0.35

    if guild.get("class_preference") == hero.hero_class:
        base += 8

    if getattr(hero, "is_developmental", False):
        base += guild.get("rookie_interest", 0) * 0.7

    if getattr(hero, "contract_attitude", "") == "Mercenary":
        base += 4
    if getattr(hero, "contract_attitude", "") == "Noble":
        base += 2 + (guild.get("prestige", 0) * 0.25)

    return max(25.0, min(95.0, base))


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
    header = f"=== Contract Round {state.contract_round} ==="
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

    signed_to_player = []
    signed_elsewhere = []

    processed_names = set()

    for hero in offered_heroes:
        processed_names.add(hero.name)
        offer = offers_by_name[hero.name]

        campaigns = int(offer["offered_campaigns"])
        signing_fee = int(offer["offered_signing_fee"])

        player_score = evaluate_offer_score(state, hero, campaigns, signing_fee)
        rival_score = estimate_rival_offer_score(state, hero)
        rival_name = rival_guild_name_for_hero(state, hero)

        if open_slots <= 0:
            message = f"{hero.name}: no roster space remained, so the offer failed."
            results.append(message)
            add_market_history_entry(state, message)
            continue

        if remaining_gold < signing_fee:
            message = f"{hero.name}: not enough gold remained to honor the offer."
            results.append(message)
            add_market_history_entry(state, message)
            continue

        if rival_score is None or player_score >= rival_score:
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
            signed_elsewhere.append(hero)
            add_hero_to_rival_guild(state, rival_name, hero)

            message = (
                f"{hero.name} signed with {rival_name}. "
                f"Your offer {grade_for_score(player_score)} vs rivals {grade_for_score(rival_score)}."
            )
            results.append(message)
            add_market_history_entry(state, message)

    for hero in current_market:
        if hero.name in processed_names:
            continue

        rival_score = estimate_rival_offer_score(state, hero)
        rival_name = rival_guild_name_for_hero(state, hero)

        if rival_score is not None and rival_score >= 62:
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
    state.contract_round += 1
    state.contract_offers = []

    signed_names = {hero.name for hero in signed_to_player}
    rival_names = {hero.name for hero in signed_elsewhere}

    remaining_market = [
        hero
        for hero in current_market
        if hero.name not in signed_names and hero.name not in rival_names
    ]

    rookie_count = max(3, len(signed_to_player) + len(signed_elsewhere))
    rookies = generate_fallback_contract_market(state, count=rookie_count)

    existing_names = {hero.name for hero in remaining_market}
    rookie_additions = [hero for hero in rookies if hero.name not in existing_names]

    state.available_contracts = remaining_market + rookie_additions

    if not signed_to_player:
        message = "You did not sign any heroes this round."
        results.append(message)
        add_market_history_entry(state, message)
    else:
        message = f"You signed {len(signed_to_player)} hero(es) this round."
        results.append(message)
        add_market_history_entry(state, message)

    message = (
        f"Remaining recruits carried over: {len(remaining_market)}. "
        f"New rookies added: {len(rookie_additions)}."
    )
    results.append(message)
    add_market_history_entry(state, message)

    return results