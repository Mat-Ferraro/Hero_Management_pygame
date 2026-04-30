from typing import List

from systems.contract_negotiation import (
    ensure_contract_state,
    evaluate_renewal_offer_score,
    get_renewal_offer_for_hero,
    renewal_acceptance_threshold,
)
from systems.rival_guilds import add_market_history_entry


def ensure_contract_fields(hero) -> None:
    if not hasattr(hero, "contract_years"):
        hero.contract_years = 1

    hero.contract_years = max(0, int(hero.contract_years))


def decrement_contracts_for_party(party) -> List[str]:
    messages: List[str] = []

    seen_ids = set()
    for hero in party:
        hero_id = id(hero)
        if hero_id in seen_ids:
            continue
        seen_ids.add(hero_id)

        ensure_contract_fields(hero)

        if getattr(hero, "health_status", lambda: "")() == "DEAD":
            continue

        if hero.contract_years > 0:
            hero.contract_years -= 1
            messages.append(
                f"{hero.name}'s contract now has {hero.contract_years} campaign(s) remaining."
            )

    return messages


def is_expiring_hero(hero) -> bool:
    ensure_contract_fields(hero)
    return hero.contract_years <= 1


def resolve_renewals_and_expirations(state) -> List[str]:
    ensure_contract_state(state)

    messages: List[str] = []
    processed_names = set()

    for hero in list(state.roster):
        ensure_contract_fields(hero)

        if getattr(hero, "health_status", lambda: "")() == "DEAD":
            continue

        if hero.contract_years > 0:
            continue

        processed_names.add(hero.name)

        offer = get_renewal_offer_for_hero(state, hero)
        if offer is None:
            state.roster.remove(hero)
            hero.satisfaction = max(40, getattr(hero, "satisfaction", 50))
            _add_hero_to_market_if_missing(state, hero)

            message = f"{hero.name}'s contract expired and they returned to the recruit market."
            messages.append(message)
            add_market_history_entry(state, message)
            continue

        campaigns = max(1, int(offer["offered_campaigns"]))
        signing_fee = max(25, int(offer["offered_signing_fee"]))

        if state.gold < signing_fee:
            state.roster.remove(hero)
            hero.satisfaction = max(35, getattr(hero, "satisfaction", 50) - 5)
            _add_hero_to_market_if_missing(state, hero)

            message = f"{hero.name}'s renewal failed because the guild could not afford {signing_fee}g."
            messages.append(message)
            add_market_history_entry(state, message)

            message = f"{hero.name} returned to the recruit market."
            messages.append(message)
            add_market_history_entry(state, message)
            continue

        player_score = evaluate_renewal_offer_score(state, hero, campaigns, signing_fee)
        required_score = renewal_acceptance_threshold(state, hero)

        if player_score >= required_score:
            state.gold -= signing_fee
            hero.contract_years = campaigns
            hero.signing_bonus = signing_fee
            hero.satisfaction = min(100, getattr(hero, "satisfaction", 50) + 4)

            message = f"{hero.name} accepted a renewal for {signing_fee}g / {campaigns}c."
            messages.append(message)
            add_market_history_entry(state, message)
        else:
            state.roster.remove(hero)
            hero.satisfaction = max(35, getattr(hero, "satisfaction", 50))
            _add_hero_to_market_if_missing(state, hero)

            message = f"{hero.name} declined the renewal offer and returned to the recruit market."
            messages.append(message)
            add_market_history_entry(state, message)

    state.renewal_offers = [
        offer
        for offer in getattr(state, "renewal_offers", [])
        if offer["hero_name"] not in processed_names
    ]

    return messages


def collect_expired_heroes(state) -> List[str]:
    return resolve_renewals_and_expirations(state)


def expired_contract_count(state) -> int:
    count = 0
    for hero in state.roster:
        ensure_contract_fields(hero)
        if hero.contract_years <= 0:
            count += 1
    return count


def _add_hero_to_market_if_missing(state, hero) -> None:
    for existing in state.available_contracts:
        if existing.name == hero.name:
            return
    state.available_contracts.append(hero)