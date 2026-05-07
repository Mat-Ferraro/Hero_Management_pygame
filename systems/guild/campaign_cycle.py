from __future__ import annotations

from typing import Iterable, List

from core.game_state import refresh_contract_market
from systems.contracts.contract_lifecycle import (
    collect_expired_heroes,
    decrement_contracts_for_party,
)
from systems.guild.rival_guilds import advance_rival_guilds, add_market_history_entry


CAMPAIGN_YEARS_PASSED = 2

PARTICIPATED_SATISFACTION_GAIN = 6
IDLE_SATISFACTION_LOSS = 4
INJURED_SATISFACTION_LOSS = 2
LOW_HEALTH_SATISFACTION_LOSS = 2


class CampaignCycleManager:
    def __init__(self, state):
        self.state = state

    def advance_cycle(self, participating_heroes: Iterable) -> List[str]:
        messages: List[str] = []

        participating_heroes = list(participating_heroes)
        participating_hero_ids = {id(hero) for hero in participating_heroes}

        messages.extend(self._log_cycle_header())
        messages.extend(self._apply_time_and_stipend())
        messages.extend(self.advance_hero_time(participating_hero_ids))
        messages.extend(decrement_contracts_for_party(participating_heroes))
        messages.extend(self.cleanup_roster())
        messages.extend(collect_expired_heroes(self.state))
        messages.extend(advance_rival_guilds(self.state, years_passed=CAMPAIGN_YEARS_PASSED))
        messages.extend(self.refresh_hiring_market())

        return [message for message in messages if message]

    def _log_cycle_header(self) -> List[str]:
        header = "=== Campaign Cycle Resolution ==="
        time_message = f"{CAMPAIGN_YEARS_PASSED} years pass across the realm."

        add_market_history_entry(self.state, header)
        add_market_history_entry(self.state, time_message)

        return [header, time_message]

    def _apply_time_and_stipend(self) -> List[str]:
        self.state.year += CAMPAIGN_YEARS_PASSED

        stipend = int(self.state.guild_upgrades.crown_stipend)
        self.state.gold += stipend

        stipend_message = f"The Crown grants the guild a {stipend}g campaign stipend."
        add_market_history_entry(self.state, stipend_message)

        return [stipend_message]

    def advance_hero_time(self, participating_hero_ids) -> List[str]:
        messages: List[str] = []

        for hero in list(self.state.roster):
            participated = id(hero) in participating_hero_ids

            old_age = int(hero.age)
            hero.age += CAMPAIGN_YEARS_PASSED
            messages.append(f"{hero.name} aged from {old_age} to {hero.age}.")

            messages.extend(self._advance_hero_injury(hero))
            messages.extend(self._apply_campaign_satisfaction(hero, participated))
            messages.extend(self._apply_low_health_penalty(hero))

            if getattr(hero, "satisfaction", 50) <= 20:
                messages.append(f"{hero.name} is considering leaving the guild.")

            hero.current_health = None
            hero.participated_this_cycle = False

        return [message for message in messages if message]

    def _advance_hero_injury(self, hero) -> List[str]:
        messages: List[str] = []

        if getattr(hero, "injured_years_remaining", 0) <= 0:
            return messages

        old_injury = int(hero.injured_years_remaining)
        hero.injured_years_remaining = max(
            0,
            old_injury - CAMPAIGN_YEARS_PASSED,
        )

        if hero.injured_years_remaining == 0:
            messages.append(f"{hero.name} recovered from injury.")
        else:
            messages.append(
                f"{hero.name} remains injured for {hero.injured_years_remaining} more year(s)."
            )

        messages.append(
            hero.adjust_satisfaction(
                -INJURED_SATISFACTION_LOSS,
                "recovering from injury",
            )
        )

        return messages

    def _apply_campaign_satisfaction(self, hero, participated: bool) -> List[str]:
        if participated:
            return [
                hero.adjust_satisfaction(
                    PARTICIPATED_SATISFACTION_GAIN,
                    "sent on campaign",
                )
            ]

        return [
            hero.adjust_satisfaction(
                -IDLE_SATISFACTION_LOSS,
                "left idle during campaign",
            )
        ]

    def _apply_low_health_penalty(self, hero) -> List[str]:
        if hero.current_health is None:
            return []

        health_percent_fn = getattr(hero, "health_percent", None)
        if not callable(health_percent_fn):
            return []

        if health_percent_fn() < 0.35:
            return [
                hero.adjust_satisfaction(
                    -LOW_HEALTH_SATISFACTION_LOSS,
                    "returned in poor condition",
                )
            ]

        return []

    def cleanup_roster(self) -> List[str]:
        messages: List[str] = []
        remaining_roster = []

        for hero in self.state.roster:
            if getattr(hero, "satisfaction", 50) <= 0:
                message = f"{hero.name} abandoned the guild due to low morale."
                messages.append(message)
                add_market_history_entry(self.state, message)
                continue

            should_retire_fn = getattr(hero, "should_retire", None)
            if callable(should_retire_fn) and should_retire_fn():
                self.state.retired_heroes.append(hero)
                message = f"{hero.name} retired from adventuring at age {hero.age}."
                messages.append(message)
                add_market_history_entry(self.state, message)
                continue

            remaining_roster.append(hero)

        self.state.roster = remaining_roster
        return messages

    def refresh_hiring_market(self) -> List[str]:
        previous_cycle = int(getattr(self.state, "market_cycle", 1))
        previous_remaining = len(getattr(self.state, "available_contracts", []))

        refresh_contract_market(self.state)

        new_cycle = int(getattr(self.state, "market_cycle", previous_cycle))
        new_pool_size = len(getattr(self.state, "available_contracts", []))

        messages: List[str] = []

        if previous_remaining > 0:
            closed_message = (
                f"The previous hiring market closed with {previous_remaining} unsigned hero(es) leaving circulation."
            )
            messages.append(closed_message)
            add_market_history_entry(self.state, closed_message)

        open_message = (
            f"Hiring market cycle {new_cycle} opened with {new_pool_size} available recruit(s)."
        )
        messages.append(open_message)
        add_market_history_entry(self.state, open_message)

        return messages