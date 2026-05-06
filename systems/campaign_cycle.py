from typing import Iterable, List

from game_state import refresh_contract_market
from systems.contract_lifecycle import (
    collect_expired_heroes,
    decrement_contracts_for_party,
)
from systems.rival_guilds import advance_rival_guilds, add_market_history_entry

CAMPAIGN_YEARS_PASSED = 2

PARTICIPATED_SATISFACTION_GAIN = 6
IDLE_SATISFACTION_LOSS = 4
INJURED_SATISFACTION_LOSS = 2
LOW_HEALTH_SATISFACTION_LOSS = 2


class CampaignCycleManager:
    def __init__(self, state):
        self.state = state

    def advance_cycle(self, participating_heroes: Iterable) -> List[str]:
        messages = []

        participating_heroes = list(participating_heroes)
        participating_hero_ids = {id(hero) for hero in participating_heroes}

        header = "=== Campaign Cycle Resolution ==="
        messages.append(header)
        add_market_history_entry(self.state, header)

        time_message = f"{CAMPAIGN_YEARS_PASSED} years pass across the realm."
        messages.append(time_message)
        add_market_history_entry(self.state, time_message)

        self.state.year += CAMPAIGN_YEARS_PASSED

        stipend = self.state.guild_upgrades.crown_stipend
        self.state.gold += stipend
        stipend_message = f"The Crown grants the guild a {stipend}g campaign stipend."
        messages.append(stipend_message)
        add_market_history_entry(self.state, stipend_message)

        messages.extend(self.advance_hero_time(participating_hero_ids))
        messages.extend(decrement_contracts_for_party(participating_heroes))
        messages.extend(self.cleanup_roster())
        messages.extend(collect_expired_heroes(self.state))
        messages.extend(advance_rival_guilds(self.state, years_passed=CAMPAIGN_YEARS_PASSED))
        messages.extend(self.refresh_hiring_market())

        return [message for message in messages if message]

    def advance_hero_time(self, participating_hero_ids) -> List[str]:
        messages = []

        for hero in list(self.state.roster):
            participated = id(hero) in participating_hero_ids

            old_age = hero.age
            hero.age += CAMPAIGN_YEARS_PASSED
            messages.append(f"{hero.name} aged from {old_age} to {hero.age}.")

            if hero.injured_years_remaining > 0:
                old_injury = hero.injured_years_remaining
                hero.injured_years_remaining = max(
                    0,
                    hero.injured_years_remaining - CAMPAIGN_YEARS_PASSED,
                )

                if hero.injured_years_remaining == 0:
                    messages.append(f"{hero.name} recovered from injury.")
                else:
                    messages.append(
                        f"{hero.name} remains injured for "
                        f"{hero.injured_years_remaining} more year(s)."
                    )

                if old_injury > 0:
                    messages.append(
                        hero.adjust_satisfaction(
                            -INJURED_SATISFACTION_LOSS,
                            "recovering from injury",
                        )
                    )

            if participated:
                messages.append(
                    hero.adjust_satisfaction(
                        PARTICIPATED_SATISFACTION_GAIN,
                        "sent on campaign",
                    )
                )
            else:
                messages.append(
                    hero.adjust_satisfaction(
                        -IDLE_SATISFACTION_LOSS,
                        "left idle during campaign",
                    )
                )

            if hero.current_health is not None and hero.health_percent() < 0.35:
                messages.append(
                    hero.adjust_satisfaction(
                        -LOW_HEALTH_SATISFACTION_LOSS,
                        "returned in poor condition",
                    )
                )

            if hero.satisfaction <= 20:
                messages.append(f"{hero.name} is considering leaving the guild.")

            hero.current_health = None
            hero.participated_this_cycle = False

        return [message for message in messages if message]

    def cleanup_roster(self) -> List[str]:
        messages = []
        remaining_roster = []

        for hero in self.state.roster:
            if hero.satisfaction <= 0:
                message = f"{hero.name} abandoned the guild due to low morale."
                messages.append(message)
                add_market_history_entry(self.state, message)
                continue

            if hero.should_retire():
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

        messages = []

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