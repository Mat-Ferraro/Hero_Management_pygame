from dataclasses import dataclass, field
from typing import Dict, List

from .ui import success, warning


CLASS_REPUTATION_KEYS = {
    "Warrior": "warrior",
    "Rogue": "rogue",
    "Cleric": "cleric",
    "Mage": "mage",
}

REPUTATION_SCORE_KEYS = (
    "overall",
    "reliability",
    "safety",
    "development",
    "protector",
    "warrior",
    "rogue",
    "cleric",
    "mage",
)

REPUTATION_MIN = -100
REPUTATION_MAX = 100
REPUTATION_HISTORY_LIMIT = 30


@dataclass
class ManagerReputation:
    overall: int = 0
    reliability: int = 0
    safety: int = 0
    development: int = 0
    protector: int = 0
    warrior: int = 0
    rogue: int = 0
    cleric: int = 0
    mage: int = 0
    history: List[str] = field(default_factory=list)

    def clamp_all(self) -> None:
        for key in REPUTATION_SCORE_KEYS:
            value = int(getattr(self, key, 0))
            setattr(self, key, max(REPUTATION_MIN, min(REPUTATION_MAX, value)))

    def scores(self) -> Dict[str, int]:
        return {key: int(getattr(self, key, 0)) for key in REPUTATION_SCORE_KEYS}

    def add_history(self, text: str) -> None:
        self.history.append(str(text))
        if len(self.history) > REPUTATION_HISTORY_LIMIT:
            self.history = self.history[-REPUTATION_HISTORY_LIMIT:]

    def adjust(self, reason: str, **changes: int) -> str:
        applied_parts = []
        negative_change_seen = False

        for key, amount in changes.items():
            if key not in REPUTATION_SCORE_KEYS:
                continue

            amount = int(amount)
            if amount == 0:
                continue

            old_value = int(getattr(self, key, 0))
            new_value = max(REPUTATION_MIN, min(REPUTATION_MAX, old_value + amount))
            setattr(self, key, new_value)

            sign = "+" if amount > 0 else ""
            applied_parts.append(f"{key} {sign}{amount}")

            if amount < 0:
                negative_change_seen = True

        self.clamp_all()

        if not applied_parts:
            return ""

        message = f"Reputation: {reason} ({', '.join(applied_parts)})."
        self.add_history(message)

        if negative_change_seen:
            return warning(message)

        return success(message)

    def adjust_class(self, hero_class: str, amount: int, reason: str) -> str:
        key = CLASS_REPUTATION_KEYS.get(hero_class)
        if not key:
            return ""

        return self.adjust(reason, **{key: int(amount)})

    def score_label(self, value: int) -> str:
        value = int(value)

        if value >= 50:
            return "Excellent"
        if value >= 20:
            return "Good"
        if value > -20:
            return "Neutral"
        if value > -50:
            return "Poor"
        return "Terrible"

    def display(self) -> str:
        lines = ["=== Manager Reputation ==="]

        for key, value in self.scores().items():
            label = self.score_label(value)
            lines.append(f"{key.title():<12}: {value:>4} ({label})")

        lines.append("")
        lines.append("Recent reputation events:")

        if not self.history:
            lines.append("  None yet.")
        else:
            for event in self.history[-10:]:
                lines.append(f"  - {event}")

        return "\n".join(lines)


def _filtered(messages: List[str]) -> List[str]:
    return [message for message in messages if message]


def reputation_for_room_outcome(
    reputation: ManagerReputation,
    room_type: str,
    combat_outcome: str,
) -> List[str]:
    messages: List[str] = []

    if room_type not in ("Monster", "Elite", "Boss"):
        return messages

    if combat_outcome == "dominant":
        messages.append(
            reputation.adjust(
                f"Dominated a {room_type.lower()} room",
                overall=1,
                safety=1,
            )
        )
    elif combat_outcome == "stable":
        messages.append(
            reputation.adjust(
                f"Cleared a {room_type.lower()} room cleanly",
                overall=1,
            )
        )
    elif combat_outcome == "rough":
        messages.append(
            reputation.adjust(
                f"Survived a costly {room_type.lower()} room",
                safety=-1,
            )
        )
    elif combat_outcome == "disaster":
        messages.append(
            reputation.adjust(
                f"Barely escaped a disastrous {room_type.lower()} room",
                overall=-1,
                safety=-2,
            )
        )

    if room_type == "Elite" and combat_outcome in ("dominant", "stable"):
        messages.append(
            reputation.adjust(
                "Handled an elite threat",
                overall=1,
                safety=1,
            )
        )

    if room_type == "Boss" and combat_outcome in ("dominant", "stable"):
        messages.append(
            reputation.adjust(
                "Handled a boss threat",
                overall=2,
                safety=1,
            )
        )

    return _filtered(messages)


def reputation_for_wound(
    reputation: ManagerReputation,
    hero_class: str,
    wound_type: str,
) -> List[str]:
    messages: List[str] = []

    if wound_type == "minor":
        messages.append(
            reputation.adjust(
                "Hero suffered a minor wound",
                safety=-1,
            )
        )
    elif wound_type == "mortal":
        messages.append(
            reputation.adjust(
                "Hero suffered a mortal wound",
                safety=-3,
                overall=-1,
            )
        )
        messages.append(
            reputation.adjust_class(
                hero_class,
                -1,
                f"{hero_class} suffered a mortal wound",
            )
        )

    return _filtered(messages)


def reputation_for_death(
    reputation: ManagerReputation,
    hero_class: str,
    is_survivor: bool,
) -> List[str]:
    messages: List[str] = []

    if is_survivor:
        messages.append(
            reputation.adjust(
                "Temporary survivor died under your command",
                safety=-3,
                protector=-4,
                overall=-2,
            )
        )
    else:
        messages.append(
            reputation.adjust(
                "Contracted hero died under your command",
                safety=-6,
                overall=-4,
            )
        )
        messages.append(
            reputation.adjust_class(
                hero_class,
                -3,
                f"{hero_class} died under your command",
            )
        )

    return _filtered(messages)


def reputation_for_survivor_rescued(reputation: ManagerReputation) -> List[str]:
    return _filtered(
        [
            reputation.adjust(
                "Safely escorted a survivor out of the dungeon",
                overall=2,
                safety=2,
                protector=4,
            )
        ]
    )


def reputation_for_debt_created(reputation: ManagerReputation) -> List[str]:
    return _filtered(
        [
            reputation.adjust(
                "Failed to pay wages on time",
                reliability=-4,
                overall=-1,
            )
        ]
    )


def reputation_for_wages_paid(reputation: ManagerReputation) -> List[str]:
    return _filtered(
        [
            reputation.adjust(
                "Paid yearly wages on time",
                reliability=1,
            )
        ]
    )


def reputation_for_level_up(reputation: ManagerReputation, hero_class: str) -> List[str]:
    return _filtered(
        [
            reputation.adjust(
                "Developed a hero through experience",
                development=2,
                overall=1,
            ),
            reputation.adjust_class(
                hero_class,
                1,
                f"Developed a {hero_class}",
            ),
        ]
    )