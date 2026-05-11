"""
core/manager_reputation.py

Tracks the guild's recent standing in the adventuring market.

Design intent (from GDD / TDD):
  - Reputation is NOT a long-term progression pillar.  That role belongs
    to the retirement-legacy system.
  - Reputation is a tiny post-campaign signal: how does the market feel
    about this guild RIGHT NOW, based on what just happened?
  - Its only mechanical effect is a slight ±5% shift on contract-acceptance
    likelihood in the hiring market.
  - Standing is a single integer clamped to [-2, +2].
  - It decays one step toward 0 at the start of each new campaign cycle so
    that the signal stays recent rather than accumulating forever.

Trigger events (the only things that should call into this module):
  Negative:
    - A contracted hero died during the campaign.
    - The guild failed too many missions in a single campaign.
  Positive:
    - All missions in the campaign were completed successfully.
    - A hero successfully retired with the guild.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .ui import success, warning


STANDING_MIN = -2
STANDING_MAX = 2
HISTORY_LIMIT = 10


@dataclass
class RecentReputation:
    """
    A single-axis measure of how the market perceives the guild after its
    most recent campaign.  Positive standing makes recruits slightly more
    willing to accept contract terms; negative standing makes them slightly
    more resistant.  The effect is intentionally small — never a hard block.
    """

    standing: int = 0
    history: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.standing = max(STANDING_MIN, min(STANDING_MAX, int(self.standing)))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clamp(self) -> None:
        self.standing = max(STANDING_MIN, min(STANDING_MAX, self.standing))

    def _record(self, message: str) -> None:
        self.history.append(message)
        if len(self.history) > HISTORY_LIMIT:
            self.history = self.history[-HISTORY_LIMIT:]

    def _adjust(self, delta: int, reason: str) -> str:
        old = self.standing
        self.standing = max(STANDING_MIN, min(STANDING_MAX, self.standing + delta))
        self._clamp()

        if self.standing == old:
            # Already at the cap in this direction; still log it.
            note = "(already at limit)"
        else:
            note = f"{old:+d} → {self.standing:+d}"

        sign = "+" if delta >= 0 else ""
        message = f"Reputation: {reason} ({sign}{delta}, standing {note})."
        self._record(message)

        return success(message) if delta > 0 else warning(message)

    # ------------------------------------------------------------------
    # Public trigger functions
    # ------------------------------------------------------------------

    def record_hero_death(self, hero_name: str) -> str:
        """A contracted hero died on campaign.  Negative signal."""
        return self._adjust(-1, f"{hero_name} died under your command")

    def record_mission_failures(self) -> str:
        """The guild failed too many missions in the campaign.  Negative signal."""
        return self._adjust(-1, "too many mission failures this campaign")

    def record_campaign_success(self) -> str:
        """All campaign missions completed successfully.  Positive signal."""
        return self._adjust(+1, "all campaign missions completed successfully")

    def record_hero_retirement(self, hero_name: str) -> str:
        """A hero retired with the guild in good standing.  Positive signal."""
        return self._adjust(+1, f"{hero_name} retired honourably with the guild")

    # ------------------------------------------------------------------
    # Cycle management
    # ------------------------------------------------------------------

    def decay(self) -> None:
        """
        Called once at the start of each new campaign cycle.
        Nudges standing one step back toward 0 so that reputation
        describes recent events, not all-time history.
        """
        if self.standing > 0:
            self.standing -= 1
        elif self.standing < 0:
            self.standing += 1

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def acceptance_modifier(self) -> float:
        """
        Returns a multiplier applied to contract-acceptance probability.
        Maps [-2, +2] linearly onto [-0.05, +0.05].

        Convention used by offer_scoring:
            acceptance_probability *= (1.0 + reputation.acceptance_modifier())
        """
        return self.standing * 0.025

    def label(self) -> str:
        """Human-readable label for UI display."""
        if self.standing >= 2:
            return "Strong"
        if self.standing == 1:
            return "Positive"
        if self.standing == 0:
            return "Neutral"
        if self.standing == -1:
            return "Poor"
        return "Troubled"

    def display(self) -> str:
        lines = [
            "=== Recent Guild Standing ===",
            f"Standing : {self.standing:+d}  ({self.label()})",
            f"Modifier : {self.acceptance_modifier():+.1%} on hire acceptance",
            "",
            "Recent events:",
        ]
        if not self.history:
            lines.append("  None yet.")
        else:
            for entry in self.history:
                lines.append(f"  - {entry}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Backward-compatibility alias
# The rest of the codebase currently references ManagerReputation in type
# annotations and save/load code.  Keeping the alias means those files only
# need a one-line find-replace rather than an immediate full audit.
# ---------------------------------------------------------------------------
ManagerReputation = RecentReputation