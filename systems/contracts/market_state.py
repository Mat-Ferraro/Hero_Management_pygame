from __future__ import annotations

from typing import Dict, List, Optional

from systems.guild.rival_guilds import ensure_rival_guild_state


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

    defaults = [
        ("money_per_campaign_weight", 0.70),
        ("term_weight", 0.10),
        ("mentorship_weight", 0.05),
        ("reputation_weight", 0.06),
        ("safety_weight", 0.03),
        ("development_weight", 0.06),
        ("market_tier", "Standard"),
        ("is_developmental", False),
    ]
    for attr_name, default_value in defaults:
        if not hasattr(hero, attr_name):
            setattr(hero, attr_name, default_value)


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

    phase = getattr(hero, "career_phase_name", lambda: None)()
    if phase is None:
        from systems.progression.hero_career import career_phase_name
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

    results: List[str] = []
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


def default_offer_for_hero(hero) -> Dict:
    ensure_hero_profile(hero)

    campaigns = max(1, int(getattr(hero, "preferred_campaigns", 3)))
    signing_fee = max(25, int(getattr(hero, "asking_signing_fee", 100)))

    return {
        "hero_name": hero.name,
        "offered_campaigns": campaigns,
        "offered_signing_fee": signing_fee,
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