from __future__ import annotations

from typing import Dict, List, Optional

from systems.guild.rival_guilds import (
    add_hero_to_rival_guild,
    add_market_history_entry,
)

from .market_state import (
    close_market_cycle,
    default_offer_for_hero,
    ensure_contract_state,
    get_offer_for_hero,
    market_stage_label,
    open_fallback_market,
)
from .offer_scoring import (
    estimate_rival_offer_score,
    evaluate_offer_score,
    grade_for_score,
    personal_acceptance_threshold,
    rival_guild_name_for_hero,
)


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

    offers_by_name: Dict[str, Dict] = {
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