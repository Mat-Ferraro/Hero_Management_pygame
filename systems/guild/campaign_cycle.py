"""
systems/guild/campaign_cycle.py

Manages the end-of-campaign cycle: time advancement, satisfaction, roster
cleanup, retirement, and market refresh.

Reputation triggers:
  - state.reputation.decay() — runs once per cycle.
  - record_hero_death() — per contracted hero death.
  - record_hero_retirement() — per successful retirement.
  - record_campaign_success() / record_mission_failures() — per cycle outcome.

Retirement legacy:
  - compute_legacy() is called at the start of each cycle.
  - apply_legacy_to_cycle() fires the legacy stipend bonus.
  - Legacy injury recovery stacks with doctrine bonus in _advance_hero_injury().
  - Legacy satisfaction bonus is applied per hero who participated.

Equipment cleanup:
  - unequip_all() called when heroes retire or abandon.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from core.game_state import refresh_contract_market
from systems.contracts.contract_lifecycle import (
    collect_expired_heroes,
    decrement_contracts_for_party,
)
from systems.equipment.equipment_rules import unequip_all
from systems.guild.retirement_legacy import apply_legacy_to_cycle, compute_legacy
from systems.guild.rival_guilds import advance_rival_guilds, add_market_history_entry


CAMPAIGN_YEARS_PASSED          = 2

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
            Heroes who went on this campaign.
        heroes_who_died:
            Contracted heroes who died; each triggers a negative reputation event.
        campaign_outcome:
            "success" | "failure" | None
        """
        messages: List[str] = []

        participating_heroes   = list(participating_heroes)
        heroes_who_died        = list(heroes_who_died or [])
        participating_hero_ids = {id(h) for h in participating_heroes}

        # Compute legacy once — used throughout the cycle.
        legacy = compute_legacy(self.state)

        # Reputation decays at the start of each cycle.
        reputation = getattr(self.state, "reputation", None)
        if reputation is not None:
            reputation.decay()

        messages.extend(self._log_cycle_header())
        messages.extend(self._apply_time_and_stipend(legacy))
        messages.extend(self._apply_death_reputation(heroes_who_died, reputation))
        messages.extend(self._apply_campaign_outcome_reputation(campaign_outcome, reputation))
        messages.extend(self.advance_hero_time(participating_hero_ids, legacy))
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
        messages: List[str] = []
        if reputation is None:
            return messages
        for hero in heroes_who_died:
            if not bool(getattr(hero, "is_temporary_survivor", False)):
                msg = reputation.record_hero_death(getattr(hero, "name", "Unknown hero"))
                if msg:
                    messages.append(msg)
        return messages

    def _apply_campaign_outcome_reputation(
        self, outcome: Optional[str], reputation
    ) -> List[str]:
        messages: List[str] = []
        if reputation is None or outcome is None:
            return messages
        if outcome == "success":
            msg = reputation.record_campaign_success()
            if msg: messages.append(msg)
        elif outcome == "failure":
            msg = reputation.record_mission_failures()
            if msg: messages.append(msg)
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

    def _apply_time_and_stipend(self, legacy) -> List[str]:
        self.state.year += CAMPAIGN_YEARS_PASSED

        # Standard Crown stipend.
        stipend = int(self.state.guild_upgrades.crown_stipend)
        self.state.gold += stipend
        messages = [f"The Crown grants the guild a {stipend}g campaign stipend."]
        add_market_history_entry(self.state, messages[0])

        # Legacy stipend bonus.
        legacy_msgs = apply_legacy_to_cycle(self.state, legacy)
        for msg in legacy_msgs:
            messages.append(msg)
            add_market_history_entry(self.state, msg)

        return messages

    def advance_hero_time(self, participating_hero_ids, legacy) -> List[str]:
        messages: List[str] = []

        # Sync guild-level equip_capacity_bonus to every hero each cycle.
        guild_eq_bonus = int(getattr(self.state.guild_upgrades, "equip_capacity_bonus", 0))

        for hero in list(self.state.roster):
            participated = id(hero) in participating_hero_ids

            # Propagate equip capacity bonus.
            hero.equip_capacity_bonus = guild_eq_bonus

            old_age   = int(hero.age)
            hero.age += CAMPAIGN_YEARS_PASSED
            messages.append(f"{hero.name} aged from {old_age} to {hero.age}.")

            messages.extend(self._advance_hero_injury(hero, legacy))
            messages.extend(self._apply_campaign_satisfaction(hero, participated, legacy))
            messages.extend(self._apply_low_health_penalty(hero))

            if getattr(hero, "satisfaction", 50) <= 20:
                messages.append(f"{hero.name} is considering leaving the guild.")

            hero.current_health          = None
            hero.participated_this_cycle = False

        return [m for m in messages if m]

    def _advance_hero_injury(self, hero, legacy) -> List[str]:
        messages: List[str] = []
        if getattr(hero, "injured_years_remaining", 0) <= 0:
            return messages

        # Doctrine bonus + legacy bonus stack.
        doctrine_bonus = int(getattr(self.state.guild_upgrades, "injury_recovery_bonus", 0))
        legacy_bonus   = int(getattr(legacy, "total_injury_recovery", 0))
        effective_recovery = CAMPAIGN_YEARS_PASSED + doctrine_bonus + legacy_bonus

        old = int(hero.injured_years_remaining)
        hero.injured_years_remaining = max(0, old - effective_recovery)

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

    def _apply_campaign_satisfaction(self, hero, participated: bool, legacy) -> List[str]:
        legacy_sat = int(getattr(legacy, "total_satisfaction_bonus", 0))
        if participated:
            total = PARTICIPATED_SATISFACTION_GAIN + legacy_sat
            return [hero.adjust_satisfaction(total, "sent on campaign")]
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
        Retiring heroes fire a positive reputation event and are added to
        state.retired_heroes (which feeds the legacy system).
        All departing heroes have gear returned to guild inventory.
        """
        messages: List[str] = []
        remaining: List     = []

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

                # Check if this retirement unlocks a new legacy milestone.
                legacy_after = compute_legacy(self.state)
                hero_class   = getattr(hero, "hero_class", "")
                old_tier     = 0  # Before this hero retired, tier may have changed.
                new_tier     = legacy_after.milestone_tier(hero_class)
                if new_tier > 0:
                    milestones = legacy_after.active_milestones.get(hero_class, [])
                    top = max(milestones, key=lambda m: m.tier, default=None)
                    if top is not None:
                        messages.append(
                            f"Legacy milestone unlocked: {hero_class} — {top.label}!"
                        )

                if reputation is not None:
                    rep_msg = reputation.record_hero_retirement(hero.name)
                    if rep_msg:
                        messages.append(rep_msg)
                continue

            remaining.append(hero)

        self.state.roster = remaining
        return messages

    def refresh_hiring_market(self) -> List[str]:
        previous_remaining = len(getattr(self.state, "available_contracts", []))
        previous_cycle     = int(getattr(self.state, "market_cycle", 1))

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