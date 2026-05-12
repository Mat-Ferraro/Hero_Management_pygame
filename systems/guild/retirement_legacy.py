"""
systems/guild/retirement_legacy.py

Retirement legacy system — retired heroes permanently improve the guild.

Design intent (TDD section 8):
  - Retired heroes provide permanent legacy bonuses.
  - Presentation is class-based milestone tracks, not individual micro-bonuses.
  - Keep it mechanically active but presentation light.
  - No death-subtraction formulas or complex legacy math.
  - Backend tracks retired hero data for future expansion.

How it works:
  Each hero class has a milestone track.  Each track has three tiers.
  Milestones unlock when enough heroes of that class have retired.
  Each milestone grants a small passive bonus to the guild.

  Milestones per class:
    Tier 1 — 1 retired hero  → small passive (e.g. +5 gold stipend)
    Tier 2 — 3 retired heroes → moderate passive
    Tier 3 — 6 retired heroes → strong passive

  Bonuses are additive across all classes.

  The legacy state is derived from state.retired_heroes on demand —
  it is never stored separately in the save file, so there is no
  migration concern.  It is computed fresh each time it is needed.

Public API:
  compute_legacy(state) -> LegacyState
    Compute the current legacy state from the roster of retired heroes.

  apply_legacy_to_cycle(state, legacy) -> List[str]
    Apply legacy bonuses that fire at cycle resolution (e.g. stipend boost).
    Called from campaign_cycle.py.

  legacy_summary_lines(legacy) -> List[str]
    Human-readable summary for UI display.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# ---------------------------------------------------------------------------
# Milestone definitions
# ---------------------------------------------------------------------------

@dataclass
class Milestone:
    tier:           int          # 1, 2, or 3
    heroes_needed:  int          # retired heroes of this class required
    label:          str          # display name
    description:    str          # what the bonus does (human-readable)
    # Concrete bonus values (applied by apply_legacy_to_cycle or read by UI).
    gold_stipend_bonus: int = 0
    xp_bonus_percent:   int = 0  # stacks with Scholarly doctrine
    recruit_quality:    int = 0  # +N to recruit level cap (display only; applied via guild_upgrades)
    injury_recovery:    int = 0  # additional injury recovery years (stacks with Militant doctrine)
    satisfaction_bonus: int = 0  # +N satisfaction on campaign participation


# Warrior milestones — toughness and leadership.
WARRIOR_MILESTONES = [
    Milestone(
        tier=1, heroes_needed=1,
        label="Veteran's Example",
        description="Retired Warriors inspire the guild. +10g Crown stipend per cycle.",
        gold_stipend_bonus=10,
    ),
    Milestone(
        tier=2, heroes_needed=3,
        label="Battle Hardened",
        description="The guild's warcraft is renowned. +20g stipend and heroes recover 1 extra year.",
        gold_stipend_bonus=20,
        injury_recovery=1,
    ),
    Milestone(
        tier=3, heroes_needed=6,
        label="Iron Brotherhood",
        description="A proud martial tradition. +30g stipend, +1 recovery, heroes gain +5 satisfaction from campaigns.",
        gold_stipend_bonus=30,
        injury_recovery=1,
        satisfaction_bonus=5,
    ),
]

# Rogue milestones — efficiency and networks.
ROGUE_MILESTONES = [
    Milestone(
        tier=1, heroes_needed=1,
        label="Street Connections",
        description="Retired Rogues leave behind useful contacts. Heroes gain +5% XP.",
        xp_bonus_percent=5,
    ),
    Milestone(
        tier=2, heroes_needed=3,
        label="Shadow Network",
        description="The guild's intelligence network grows. +10% XP and +10g stipend.",
        xp_bonus_percent=10,
        gold_stipend_bonus=10,
    ),
    Milestone(
        tier=3, heroes_needed=6,
        label="Phantom Lodge",
        description="An unseen hand guides the guild. +15% XP, +20g stipend, +5 satisfaction.",
        xp_bonus_percent=15,
        gold_stipend_bonus=20,
        satisfaction_bonus=5,
    ),
]

# Cleric milestones — healing and morale.
CLERIC_MILESTONES = [
    Milestone(
        tier=1, heroes_needed=1,
        label="Healing Hands",
        description="Retired Clerics bless the guild. Heroes recover 1 extra year from injuries.",
        injury_recovery=1,
    ),
    Milestone(
        tier=2, heroes_needed=3,
        label="Sacred Tradition",
        description="The guild carries a spiritual legacy. +1 recovery and +5 satisfaction.",
        injury_recovery=1,
        satisfaction_bonus=5,
    ),
    Milestone(
        tier=3, heroes_needed=6,
        label="Order of the Vigil",
        description="A healing order protects the guild. +2 recovery, +10 satisfaction, +10g stipend.",
        injury_recovery=2,
        satisfaction_bonus=10,
        gold_stipend_bonus=10,
    ),
]

# Mage milestones — knowledge and power.
MAGE_MILESTONES = [
    Milestone(
        tier=1, heroes_needed=1,
        label="Arcane Records",
        description="Retired Mages leave their research. Heroes gain +10% XP.",
        xp_bonus_percent=10,
    ),
    Milestone(
        tier=2, heroes_needed=3,
        label="Spellcraft Tradition",
        description="The guild masters arcane knowledge. +15% XP and +10g stipend.",
        xp_bonus_percent=15,
        gold_stipend_bonus=10,
    ),
    Milestone(
        tier=3, heroes_needed=6,
        label="Grand Conclave",
        description="A legendary arcane tradition. +20% XP, +20g stipend, +5 satisfaction.",
        xp_bonus_percent=20,
        gold_stipend_bonus=20,
        satisfaction_bonus=5,
    ),
]

CLASS_MILESTONES: Dict[str, List[Milestone]] = {
    "Warrior": WARRIOR_MILESTONES,
    "Rogue":   ROGUE_MILESTONES,
    "Cleric":  CLERIC_MILESTONES,
    "Mage":    MAGE_MILESTONES,
}


# ---------------------------------------------------------------------------
# Legacy state
# ---------------------------------------------------------------------------

@dataclass
class LegacyState:
    """
    Computed snapshot of the guild's retirement legacy bonuses.
    Derived from state.retired_heroes — never persisted separately.
    """

    # Count of retired heroes per class.
    retired_counts: Dict[str, int] = field(default_factory=dict)

    # Active milestones per class (those whose heroes_needed threshold is met).
    active_milestones: Dict[str, List[Milestone]] = field(default_factory=dict)

    # Aggregated bonus totals across all active milestones.
    total_gold_stipend_bonus: int = 0
    total_xp_bonus_percent:   int = 0
    total_injury_recovery:    int = 0
    total_satisfaction_bonus: int = 0

    def has_any_legacy(self) -> bool:
        return any(self.retired_counts.values())

    def milestone_tier(self, hero_class: str) -> int:
        """Current milestone tier for a class (0 = none unlocked)."""
        milestones = self.active_milestones.get(hero_class, [])
        return max((m.tier for m in milestones), default=0)

    def next_milestone(self, hero_class: str) -> Milestone | None:
        """Return the next not-yet-unlocked milestone for a class, or None."""
        count      = self.retired_counts.get(hero_class, 0)
        all_milestones = CLASS_MILESTONES.get(hero_class, [])
        for m in sorted(all_milestones, key=lambda x: x.tier):
            if count < m.heroes_needed:
                return m
        return None


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------

def compute_legacy(state) -> LegacyState:
    """
    Derive the current legacy state from state.retired_heroes.
    Cheap to call — O(n) where n = len(state.retired_heroes).
    """
    retired_heroes = list(getattr(state, "retired_heroes", []))

    counts: Dict[str, int] = {}
    for hero in retired_heroes:
        hero_class = getattr(hero, "hero_class", "Unknown")
        counts[hero_class] = counts.get(hero_class, 0) + 1

    active: Dict[str, List[Milestone]] = {}
    total_stipend   = 0
    total_xp        = 0
    total_recovery  = 0
    total_sat       = 0

    for hero_class, milestones in CLASS_MILESTONES.items():
        count   = counts.get(hero_class, 0)
        unlocked = [m for m in milestones if count >= m.heroes_needed]
        if unlocked:
            active[hero_class] = unlocked
            # Use the highest-tier milestone's values per bonus type
            # (they're designed to be cumulative in description but we
            # take the max to avoid double-stacking the same tier).
            total_stipend  += max(m.gold_stipend_bonus for m in unlocked)
            total_xp       += max(m.xp_bonus_percent   for m in unlocked)
            total_recovery += max(m.injury_recovery     for m in unlocked)
            total_sat      += max(m.satisfaction_bonus  for m in unlocked)

    return LegacyState(
        retired_counts=counts,
        active_milestones=active,
        total_gold_stipend_bonus=total_stipend,
        total_xp_bonus_percent=total_xp,
        total_injury_recovery=total_recovery,
        total_satisfaction_bonus=total_sat,
    )


# ---------------------------------------------------------------------------
# Cycle application
# ---------------------------------------------------------------------------

def apply_legacy_to_cycle(state, legacy: LegacyState) -> List[str]:
    """
    Apply legacy bonuses that trigger at the start of each campaign cycle.
    Currently: extra Crown stipend.

    Called by CampaignCycleManager.advance_cycle() after the standard stipend.
    Returns a list of log messages.
    """
    messages: List[str] = []

    if legacy.total_gold_stipend_bonus > 0:
        state.gold += legacy.total_gold_stipend_bonus
        messages.append(
            f"Retirement legacy grants +{legacy.total_gold_stipend_bonus}g "
            f"from retired heroes."
        )

    return messages


def effective_xp_bonus_percent(state, legacy: LegacyState) -> int:
    """
    Combined XP bonus from legacy + guild doctrine upgrade.
    Used by campaign_runtime.complete_task() when awarding mission XP.
    """
    doctrine_bonus = int(getattr(state.guild_upgrades, "xp_bonus_percent", 0))
    return doctrine_bonus + legacy.total_xp_bonus_percent


def effective_injury_recovery(state, legacy: LegacyState) -> int:
    """
    Combined injury recovery bonus from legacy + guild doctrine upgrade.
    Used by campaign_cycle._advance_hero_injury().
    """
    doctrine_bonus = int(getattr(state.guild_upgrades, "injury_recovery_bonus", 0))
    return doctrine_bonus + legacy.total_injury_recovery


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def legacy_summary_lines(legacy: LegacyState) -> List[str]:
    """
    Short human-readable summary of active milestones.
    Suitable for display in the game hub or a dedicated legacy panel.
    """
    if not legacy.has_any_legacy():
        return ["No retired heroes yet.  Retire heroes to build a lasting legacy."]

    lines: List[str] = []

    for hero_class, milestones in legacy.active_milestones.items():
        top = max(milestones, key=lambda m: m.tier)
        count = legacy.retired_counts.get(hero_class, 0)
        lines.append(f"{hero_class}: {top.label} (Tier {top.tier}, {count} retired)")

    if lines:
        lines.append("")

    if legacy.total_gold_stipend_bonus > 0:
        lines.append(f"  +{legacy.total_gold_stipend_bonus}g Crown stipend per cycle")
    if legacy.total_xp_bonus_percent > 0:
        lines.append(f"  +{legacy.total_xp_bonus_percent}% mission XP")
    if legacy.total_injury_recovery > 0:
        lines.append(f"  -{legacy.total_injury_recovery} yr injury recovery time")
    if legacy.total_satisfaction_bonus > 0:
        lines.append(f"  +{legacy.total_satisfaction_bonus} campaign satisfaction")

    return lines


def legacy_milestone_rows(legacy: LegacyState) -> List[tuple]:
    """
    List of (label, value_string) pairs for display in a KeyValueGrid.
    Includes both unlocked milestones and the next milestone to unlock.
    """
    rows = []

    for hero_class, milestones in CLASS_MILESTONES.items():
        count = legacy.retired_counts.get(hero_class, 0)
        top   = max((m for m in milestones if count >= m.heroes_needed),
                    key=lambda m: m.tier, default=None)
        nxt   = legacy.next_milestone(hero_class)

        if top is not None:
            rows.append((f"{hero_class} Legacy", f"Tier {top.tier}: {top.label}"))
        elif nxt is not None:
            rows.append((f"{hero_class} Legacy",
                         f"Tier 1 in {nxt.heroes_needed - count} more retirement(s)"))

    return rows