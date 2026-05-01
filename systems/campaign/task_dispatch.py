from __future__ import annotations

from typing import Iterable, List, Optional

from .campaign_constants import (
    CAMPAIGN_HOME_BASE_POSITION,
    HERO_STATE_AVAILABLE,
    HERO_STATE_RESTING,
    HERO_STATE_RETURNING,
    HERO_STATE_TRAVELING,
    TASK_STATE_PENDING,
    TASK_STATE_TRAVELING_TO,
)
from .campaign_models import CampaignRuntime, HeroDispatchState


def find_task(runtime: CampaignRuntime, task_id: str):
    for task in runtime.active_tasks:
        if task.task_id == task_id:
            return task
    return None


def get_or_create_hero_dispatch_state(runtime: CampaignRuntime, hero_name: str) -> HeroDispatchState:
    existing = runtime.hero_states.get(hero_name)
    if existing is not None:
        return existing

    state = HeroDispatchState(
        hero_name=hero_name,
        state=HERO_STATE_AVAILABLE,
        current_position=CAMPAIGN_HOME_BASE_POSITION,
    )
    runtime.hero_states[hero_name] = state
    return state


def can_assign_hero_to_task(runtime: CampaignRuntime, hero_name: str) -> tuple[bool, str]:
    state = get_or_create_hero_dispatch_state(runtime, hero_name)

    if state.state != HERO_STATE_AVAILABLE:
        return False, f"{hero_name} is not available."

    return True, ""


def can_assign_party_to_task(
    runtime: CampaignRuntime,
    hero_names: Iterable[str],
    task_id: str,
) -> tuple[bool, str]:
    task = find_task(runtime, task_id)
    if task is None:
        return False, "Task not found."

    hero_names = list(hero_names)

    if task.state != TASK_STATE_PENDING:
        return False, "Task is no longer assignable."

    if not hero_names:
        return False, "No heroes selected."

    if len(hero_names) > task.max_heroes:
        return False, f"This task allows only {task.max_heroes} heroes."

    if len(set(hero_names)) != len(hero_names):
        return False, "Duplicate hero selection is not allowed."

    for hero_name in hero_names:
        allowed, reason = can_assign_hero_to_task(runtime, hero_name)
        if not allowed:
            return False, reason

    return True, ""


def assign_heroes_to_task(
    runtime: CampaignRuntime,
    hero_names: List[str],
    task_id: str,
    now: float,
) -> tuple[bool, str]:
    allowed, reason = can_assign_party_to_task(runtime, hero_names, task_id)
    if not allowed:
        return False, reason

    task = find_task(runtime, task_id)
    if task is None:
        return False, "Task not found."

    task.state = TASK_STATE_TRAVELING_TO
    task.assigned_heroes = list(hero_names)
    task.started_at = None
    task.active_until = None
    task.completed_at = None
    task.failed_reason = ""
    task.outcome_band = ""
    task.success_chance = 0.0
    task.coverage_ratio = 0.0
    task.payout_multiplier = 1.0
    task.xp_multiplier = 1.0

    for hero_name in hero_names:
        hero_state = get_or_create_hero_dispatch_state(runtime, hero_name)
        hero_state.state = HERO_STATE_TRAVELING
        hero_state.assigned_task_id = task.task_id
        hero_state.travel_end_time = now + task.travel_time
        hero_state.task_end_time = None
        hero_state.return_end_time = None
        hero_state.rest_end_time = None
        hero_state.current_position = CAMPAIGN_HOME_BASE_POSITION

    runtime.event_log.append(
        f"Assigned {', '.join(hero_names)} to {task.task_type} ({task.task_id})."
    )
    return True, f"Assigned {', '.join(hero_names)}."


def start_hero_return(
    runtime: CampaignRuntime,
    hero_name: str,
    task_id: Optional[str],
    now: float,
    return_time: float,
) -> None:
    hero_state = get_or_create_hero_dispatch_state(runtime, hero_name)
    hero_state.state = HERO_STATE_RETURNING
    hero_state.assigned_task_id = task_id
    hero_state.travel_end_time = None
    hero_state.task_end_time = None
    hero_state.return_end_time = now + return_time
    hero_state.rest_end_time = None


def start_hero_rest(
    runtime: CampaignRuntime,
    hero_name: str,
    now: float,
    rest_duration: float,
) -> None:
    hero_state = get_or_create_hero_dispatch_state(runtime, hero_name)
    hero_state.state = HERO_STATE_RESTING
    hero_state.assigned_task_id = None
    hero_state.travel_end_time = None
    hero_state.task_end_time = None
    hero_state.return_end_time = None
    hero_state.rest_end_time = now + rest_duration
    hero_state.current_position = CAMPAIGN_HOME_BASE_POSITION


def release_hero_to_available(runtime: CampaignRuntime, hero_name: str) -> None:
    hero_state = get_or_create_hero_dispatch_state(runtime, hero_name)
    hero_state.state = HERO_STATE_AVAILABLE
    hero_state.assigned_task_id = None
    hero_state.travel_end_time = None
    hero_state.task_end_time = None
    hero_state.return_end_time = None
    hero_state.rest_end_time = None
    hero_state.current_position = CAMPAIGN_HOME_BASE_POSITION