from typing import Iterable, List


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

        participating_hero_ids = {id(hero) for hero in participating_heroes}

        messages.append("=== Campaign Cycle Resolution ===")
        messages.append(f"{CAMPAIGN_YEARS_PASSED} years pass across the realm.")

        self.state.year += CAMPAIGN_YEARS_PASSED

        stipend = self.state.guild_upgrades.crown_stipend
        self.state.gold += stipend
        messages.append(f"The Crown grants the guild a {stipend}g campaign stipend.")

        messages.extend(self.advance_hero_time(participating_hero_ids))
        messages.extend(self.cleanup_roster())

        return messages

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
                messages.append(
                    f"{hero.name} abandoned the guild due to low morale."
                )
                continue

            if hero.should_retire():
                self.state.retired_heroes.append(hero)
                messages.append(f"{hero.name} retired from adventuring at age {hero.age}.")
                continue

            remaining_roster.append(hero)

        self.state.roster = remaining_roster
        return messages