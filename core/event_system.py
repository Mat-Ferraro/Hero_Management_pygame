import random
from copy import deepcopy
from typing import Any, Dict, List, Optional

from data_loader import load_events


DEFAULT_EVENT = {
    "name": "Empty Chamber",
    "description": "The party finds a quiet room and nothing else.",
    "choices": [
        {
            "id": "move_on",
            "label": "Move on",
            "outcome": "nothing",
            "reputation": {},
            "message": "Nothing happens.",
            "next_event_id": None,
            "branch_flags": {},
            "linked_tasks": [],
            "reward_modifiers": {},
            "tags": [],
        }
    ],
    "branch_flags": {},
    "linked_tasks": [],
    "meta": {},
}


def choose_event_for_enemy(enemy_type: str) -> Dict[str, Any]:
    events = load_events()
    matching_events = [
        event
        for event in events
        if enemy_type in event.get("enemy_types", []) or not event.get("enemy_types")
    ]

    if not matching_events:
        return build_runtime_event(DEFAULT_EVENT, enemy_type=enemy_type)

    chosen = random.choice(matching_events)
    return build_runtime_event(chosen, enemy_type=enemy_type)


def build_runtime_event(event_data: Dict[str, Any], enemy_type: str | None = None) -> Dict[str, Any]:
    source = deepcopy(event_data or DEFAULT_EVENT)

    event_name = str(source.get("name", "Unknown Event")).strip() or "Unknown Event"
    description = str(source.get("description", "")).strip()
    enemy_types = list(source.get("enemy_types", []))
    raw_choices = source.get("choices", [])

    return {
        "event_id": source.get("event_id") or slugify(event_name),
        "name": event_name,
        "description": description,
        "enemy_types": enemy_types,
        "enemy_type": enemy_type,
        "choices": normalize_choices(raw_choices),
        "branch_flags": dict(source.get("branch_flags", {})),
        "linked_tasks": list(source.get("linked_tasks", [])),
        "meta": dict(source.get("meta", {})),
    }


def normalize_choices(raw_choices: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_choices, list) or not raw_choices:
        raw_choices = DEFAULT_EVENT["choices"]

    normalized: List[Dict[str, Any]] = []

    for index, raw_choice in enumerate(raw_choices):
        if not isinstance(raw_choice, dict):
            continue

        label = str(raw_choice.get("label", f"Choice {index + 1}")).strip() or f"Choice {index + 1}"
        choice_id = raw_choice.get("id") or f"{slugify(label)}_{index + 1}"

        normalized.append(
            {
                "id": str(choice_id),
                "label": label,
                "outcome": str(raw_choice.get("outcome", "nothing")),
                "message": str(raw_choice.get("message", "The party makes a choice.")),
                "reputation": dict(raw_choice.get("reputation", {})),
                "next_event_id": raw_choice.get("next_event_id"),
                "branch_flags": dict(raw_choice.get("branch_flags", {})),
                "linked_tasks": list(raw_choice.get("linked_tasks", [])),
                "reward_modifiers": dict(raw_choice.get("reward_modifiers", {})),
                "tags": list(raw_choice.get("tags", [])),
            }
        )

    if normalized:
        return normalized

    return deepcopy(DEFAULT_EVENT["choices"])


def event_choices(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(event.get("choices", []))


def first_event_choice(event: Dict[str, Any]) -> Dict[str, Any]:
    choices = event_choices(event)
    if choices:
        return choices[0]
    return deepcopy(DEFAULT_EVENT["choices"][0])


def find_event_choice(event: Dict[str, Any], choice_id: str) -> Optional[Dict[str, Any]]:
    normalized_choice_id = str(choice_id).strip()
    if not normalized_choice_id:
        return None

    for choice in event_choices(event):
        if str(choice.get("id", "")).strip() == normalized_choice_id:
            return choice

    return None


def choice_index_is_valid(event: Dict[str, Any], index: int) -> bool:
    choices = event_choices(event)
    return 0 <= index < len(choices)


def choice_by_index(event: Dict[str, Any], index: int) -> Dict[str, Any]:
    choices = event_choices(event)
    if 0 <= index < len(choices):
        return choices[index]
    return first_event_choice(event)


def describe_event_choice(choice: Dict[str, Any]) -> str:
    return str(choice.get("message", "The party makes a choice."))


def event_summary_lines(event: Dict[str, Any]) -> List[str]:
    lines = [str(event.get("name", "Unknown Event"))]

    description = str(event.get("description", "")).strip()
    if description:
        lines.append(description)

    for index, choice in enumerate(event_choices(event), start=1):
        lines.append(f"{index}. {choice.get('label', 'Unknown choice')}")

    return lines


def apply_event_reputation(state, reputation_changes: Dict[str, int], reason: str) -> List[str]:
    if not reputation_changes:
        return []

    message = state.reputation.adjust(reason, **reputation_changes)
    return [message] if message else []


def apply_choice_consequences(
    state,
    choice: Dict[str, Any],
    reason: str | None = None,
) -> Dict[str, Any]:
    applied_reason = reason or f"Event choice: {choice.get('label', 'Unknown choice')}"

    reputation_messages = apply_event_reputation(
        state=state,
        reputation_changes=dict(choice.get("reputation", {})),
        reason=applied_reason,
    )

    return {
        "choice_id": choice.get("id"),
        "outcome": choice.get("outcome", "nothing"),
        "message": describe_event_choice(choice),
        "reputation_messages": reputation_messages,
        "branch_flags": dict(choice.get("branch_flags", {})),
        "linked_tasks": list(choice.get("linked_tasks", [])),
        "reward_modifiers": dict(choice.get("reward_modifiers", {})),
        "next_event_id": choice.get("next_event_id"),
        "tags": list(choice.get("tags", [])),
    }


def slugify(text: str) -> str:
    cleaned = []
    last_was_sep = False

    for char in str(text).lower():
        if char.isalnum():
            cleaned.append(char)
            last_was_sep = False
        elif not last_was_sep:
            cleaned.append("_")
            last_was_sep = True

    slug = "".join(cleaned).strip("_")
    return slug or "event"