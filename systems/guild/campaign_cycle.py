"""
systems/guild/campaign_cycle.py

Manages the end-of-campaign cycle: time advancement, satisfaction, roster
cleanup, retirement, and market refresh.

Reputation triggers (added in this version):
  - state.reputation.decay() — called once at the top of advance_cycle so
    standing drifts back toward neutral each cycle.
  - record_hero_death() — called when a contracted hero dies (not temporaries).
  - record_hero_retirement() — called when a hero retires via should_retire().
  - record_campaign_success() / record_mission_failures() — called based on
    the campaign outcome summary passed into advance_cycle.

  The caller (campaign_runtime / the scene that ends a campaign) is responsible
  for passing outcome data.  advance_cycle() accepts two new optional arguments:
    - heroes_who_died: list of Hero objects that died this campaign.
    - campaign_outcome: "success" | "failure" | None (unknown / not tracked).
  Both default to safe values so existing call sites need no changes.

Equipment cleanup:
  When a hero retires or abandons the guild, unequip_all() is called so
  their gear returns to the guild inventory automatically.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from core.game_state import refresh_contract_market
from systems.contracts.contract_lifecycle import (
    collect_expired_heroes,
    decrement_contracts_for_party,
)
from systems.equipment.equipment_rules import unequip_all
from systems.guild.rival_guilds import advance_rival_guilds, add_market_history_entry


CAMPAIGN_YEARS_PASSED       = 2

PARTICIPATED_SATISFACTION_GAIN = 6
IDLE_SATISFACTION_LOSS         = 4
INJURED_SATISFACTION_LOSS      = 2
LOW_HEALTH_SATISFACTION_LOSS   = 2


class CampaignCycleManager:
    def __init__(self, state):
        self.state = state

    def advance_cycle(
        self,
        participating_heroes: Iterable,
        heroes_who_died: Optional[List] = None,
        campaign_outcome: Optional[str] = None,
    ) -> List[str]:
        """
        Resolve a completed campaign cycle.

        Parameters
        ----------
        participating_heroes:
            Heroes who went on this campaign (used for satisfaction and
            contract decrements).
        heroes_who_died:
            Contracted heroes who died during the campaign.  Each triggers
            a negative reputation event.  Defaults to empty list.
        campaign_outcome:
            "success"  — all missions completed.  Positive reputation event.
            "failure"  — too many missions failed.  Negative reputation event.
            None       — outcome unknown or not tracked; no reputation change.
        """
        messages: List[str] = []

        participating_heroes  = list(participating_heroes)
        heroes_who_died       = list(heroes_who_died or [])
        participating_hero_ids = {id(h) for h in participating_heroes}

        # Reputation decays at the start of each cycle — keeps standing recent.
        reputation = getattr(self.state, "reputation", None)
        if reputation is not None:
            reputation.decay()

        messages.extend(self._log_cycle_header())
        messages.extend(self._apply_time_and_stipend())
        messages.extend(self._apply_death_reputation(heroes_who_died, reputation))
        messages.extend(self._apply_campaign_outcome_reputation(campaign_outcome, reputation))
        messages.extend(self.advance_hero_time(participating_hero_ids))
        messages.extend(decrement_contracts_for_party(participating_heroes))
        messages.extend(self.cleanup_roster(reputation))
        messages.extend(collect_expired_heroes(self.state))
        messages.extend(advance_rival_guilds(self.state, years_passed=CAMPAIGN_YEARS_PASSED))
        messages.extend(self.refresh_hiring_market())

        return [m for m in messages if m]

    # ------------------------------------------------------------------
    # Reputation helpers
    # ------------------------------------------------------------------

    def _apply_death_reputation(self, heroes_who_died: List, reputation) -> List[str]:
        """Fire a negative reputation event for each contracted hero death."""
        messages: List[str] = []
        if reputation is None:
            return messages
        for hero in heroes_who_died:
            is_temp = bool(getattr(hero, "is_temporary_survivor", False))
            if not is_temp:
                msg = reputation.record_hero_death(getattr(hero, "name", "Unknown hero"))
                if msg:
                    messages.append(msg)
        return messages

    def _apply_campaign_outcome_reputation(
        self, outcome: Optional[str], reputation
    ) -> List[str]:
        """Apply reputation for overall campaign result."""
        messages: List[str] = []
        if reputation is None or outcome is None:
            return messages
        if outcome == "success":
            msg = reputation.record_campaign_success()
            if msg:
                messages.append(msg)
        elif outcome == "failure":
            msg = reputation.record_mission_failures()
            if msg:
                messages.append(msg)
        return messages

    # ------------------------------------------------------------------
    # Cycle stages
    # ------------------------------------------------------------------

    def _log_cycle_header(self) -> List[str]:
        header       = "=== Campaign Cycle Resolution ==="
        time_message = f"{CAMPAIGN_YEARS_PASSED} years pass across the realm."
        add_market_history_entry(self.state, header)
        add_market_history_entry(self.state, time_message)
        return [header, time_message]

    def _apply_time_and_stipend(self) -> List[str]:
        self.state.year += CAMPAIGN_YEARS_PASSED
        stipend = int(self.state.guild_upgrades.crown_stipend)
        self.state.gold += stipend
        msg = f"The Crown grants the guild a {stipend}g campaign stipend."
        add_market_history_entry(self.state, msg)
        return [msg]

    def advance_hero_time(self, participating_hero_ids) -> List[str]:
        messages: List[str] = []
        for hero in list(self.state.roster):
            participated = id(hero) in participating_hero_ids

            old_age   = int(hero.age)
            hero.age += CAMPAIGN_YEARS_PASSED
            messages.append(f"{hero.name} aged from {old_age} to {hero.age}.")

            messages.extend(self._advance_hero_injury(hero))
            messages.extend(self._apply_campaign_satisfaction(hero, participated))
            messages.extend(self._apply_low_health_penalty(hero))

            if getattr(hero, "satisfaction", 50) <= 20:
                messages.append(f"{hero.name} is considering leaving the guild.")

            hero.current_health        = None
            hero.participated_this_cycle = False

        return [m for m in messages if m]

    def _advance_hero_injury(self, hero) -> List[str]:
        messages: List[str] = []
        if getattr(hero, "injured_years_remaining", 0) <= 0:
            return messages
        old = int(hero.injured_years_remaining)
        hero.injured_years_remaining = max(0, old - CAMPAIGN_YEARS_PASSED)
        if hero.injured_years_remaining == 0:
            messages.append(f"{hero.name} recovered from injury.")
        else:
            messages.append(
                f"{hero.name} remains injured for {hero.injured_years_remaining} more year(s)."
            )
        messages.append(
            hero.adjust_satisfaction(-INJURED_SATISFACTION_LOSS, "recovering from injury")
        )
        return messages

    def _apply_campaign_satisfaction(self, hero, participated: bool) -> List[str]:
        if participated:
            return [hero.adjust_satisfaction(PARTICIPATED_SATISFACTION_GAIN, "sent on campaign")]
        return [hero.adjust_satisfaction(-IDLE_SATISFACTION_LOSS, "left idle during campaign")]

    def _apply_low_health_penalty(self, hero) -> List[str]:
        if hero.current_health is None:
            return []
        hp_fn = getattr(hero, "health_percent", None)
        if not callable(hp_fn):
            return []
        if hp_fn() < 0.35:
            return [
                hero.adjust_satisfaction(-LOW_HEALTH_SATISFACTION_LOSS, "returned in poor condition")
            ]
        return []

    def cleanup_roster(self, reputation=None) -> List[str]:
        """
        Remove heroes who quit (satisfaction ≤ 0) or hit retirement age.

        Retiring heroes:
          - Gear is returned to guild inventory via unequip_all().
          - A positive reputation event fires.
          - Hero is added to state.retired_heroes.

        Abandoned heroes:
          - Gear is also returned.
          - No reputation event (quitting isn't the same as retiring).
        """
        messages: List[str] = []
        remaining: List = []

        for hero in self.state.roster:
            if getattr(hero, "satisfaction", 50) <= 0:
                unequip_all(hero, self.state.inventory)
                msg = f"{hero.name} abandoned the guild due to low morale."
                messages.append(msg)
                add_market_history_entry(self.state, msg)
                continue

            should_retire_fn = getattr(hero, "should_retire", None)
            if callable(should_retire_fn) and should_retire_fn():
                unequip_all(hero, self.state.inventory)
                self.state.retired_heroes.append(hero)
                msg = f"{hero.name} retired from adventuring at age {hero.age}."
                messages.append(msg)
                add_market_history_entry(self.state, msg)

                # Positive reputation event for successful retirement.
                if reputation is not None:
                    rep_msg = reputation.record_hero_retirement(hero.name)
                    if rep_msg:
                        messages.append(rep_msg)
                continue

            remaining.append(hero)

        self.state.roster = remaining
        return messages

    def refresh_hiring_market(self) -> List[str]:
        previous_cycle     = int(getattr(self.state, "market_cycle", 1))
        previous_remaining = len(getattr(self.state, "available_contracts", []))

        refresh_contract_market(self.state)

        new_cycle     = int(getattr(self.state, "market_cycle", previous_cycle))
        new_pool_size = len(getattr(self.state, "available_contracts", []))

        messages: List[str] = []

        if previous_remaining > 0:
            msg = (
                f"The previous hiring market closed with "
                f"{previous_remaining} unsigned hero(es) leaving circulation."
            )
            messages.append(msg)
            add_market_history_entry(self.state, msg)

        msg = f"Hiring market cycle {new_cycle} opened with {new_pool_size} available recruit(s)."
        messages.append(msg)
        add_market_history_entry(self.state, msg)

        return messages