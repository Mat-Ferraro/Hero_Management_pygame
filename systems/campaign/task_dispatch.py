from __future__ import annotations

from typing import Iterable

from .campaign_constants import (
    CAMPAIGN_HOME_BASE_POSITION,
    HERO_STATE_AVAILABLE,
    HERO_STATE_AWAITING_DECISION,
    HERO_STATE_ON_TASK,
    HERO_STATE_RESTING,
    HERO_STATE_RETURNING,
    HERO_STATE_TRAVELING,
    TASK_STATE_PENDING,
    TASK_STATE_TRAVELING_TO,
)
from .campaign_models import CampaignRuntime, HeroDispatchState


ASSIGNABLE_HERO_STATES = {
    HERO_STATE_AVAILABLE,
}

NON_ASSIGNABLE_HERO_STATES = {
    HERO_STATE_TRAVELING,
    HERO_STATE_ON_TASK,
    HERO_STATE_AWAITING_DECISION,
    HERO_STATE_RETURNING,
    HERO_STATE_RESTING,
}


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


def reset_hero_dispatch_timers(hero_state: HeroDispatchState) -> None:
    hero_state.travel_end_time = None
    hero_state.task_end_time = None
    hero_state.return_end_time = None
    hero_state.rest_end_time = None


def reset_task_resolution_fields(task) -> None:
    task.started_at = None
    task.active_until = None
    task.completed_at = None
    task.acknowledged_at = None

    task.failed_reason = ""
    task.outcome_band = ""
    task.success_chance = 0.0
    task.coverage_ratio = 0.0
    task.payout_multiplier = 1.0
    task.xp_multiplier = 1.0
    task.outcome_summary = ""

    task.injured_heroes = []
    task.injury_rest_by_hero = {}
    task.satisfaction_delta_by_hero = {}
    task.training_points_by_hero = {}
    task.consequence_summary = []

    task.branch_flags = {}
    task.reward_modifiers = {}


def hero_assignment_block_reason(runtime: CampaignRuntime, hero_name: str) -> str:
    hero_state = get_or_create_hero_dispatch_state(runtime, hero_name)

    if hero_state.state == HERO_STATE_AVAILABLE:
        return ""

    if hero_state.state == HERO_STATE_RESTING:
        return f"{hero_name} is resting."

    if hero_state.state == HERO_STATE_RETURNING:
        return f"{hero_name} is returning to the guild."

    if hero_state.state == HERO_STATE_TRAVELING:
        return f"{hero_name} is already traveling to a task."

    if hero_state.state == HERO_STATE_ON_TASK:
        return f"{hero_name} is already on a task."

    if hero_state.state == HERO_STATE_AWAITING_DECISION:
        return f"{hero_name} is waiting on a task decision."

    return f"{hero_name} is not available."


def can_assign_hero_to_task(runtime: CampaignRuntime, hero_name: str) -> tuple[bool, str]:
    reason = hero_assignment_block_reason(runtime, hero_name)
    if reason:
        return False, reason
    return True, ""


def task_is_assignable(task) -> bool:
    return getattr(task, "state", None) == TASK_STATE_PENDING


def can_assign_party_to_task(
    runtime: CampaignRuntime,
    hero_names: Iterable[str],
    task_id: str,
) -> tuple[bool, str]:
    task = find_task(runtime, task_id)
    if task is None:
        return False, "Task not found."

    hero_names = [str(hero_name) for hero_name in hero_names]

    if not task_is_assignable(task):
        return False, "Task is no longer assignable."

    if not hero_names:
        return False, "No heroes selected."

    if len(set(hero_names)) != len(hero_names):
        return False, "Duplicate hero selection is not allowed."

    if len(hero_names) > int(getattr(task, "max_heroes", 1)):
        return False, f"This task allows only {task.max_heroes} heroes."

    for hero_name in hero_names:
        allowed, reason = can_assign_hero_to_task(runtime, hero_name)
        if not allowed:
            return False, reason

    return True, ""


def assign_heroes_to_task(
    runtime: CampaignRuntime,
    hero_names: list[str],
    task_id: str,
    now: float,
) -> tuple[bool, str]:
    allowed, reason = can_assign_party_to_task(runtime, hero_names, task_id)
    if not allowed:
        return False, reason

    task = find_task(runtime, task_id)
    if task is None:
        return False, "Task not found."

    hero_names = [str(hero_name) for hero_name in hero_names]

    task.state = TASK_STATE_TRAVELING_TO
    task.assigned_heroes = list(hero_names)
    reset_task_resolution_fields(task)

    for hero_name in hero_names:
        hero_state = get_or_create_hero_dispatch_state(runtime, hero_name)
        hero_state.state = HERO_STATE_TRAVELING
        hero_state.assigned_task_id = task.task_id
        hero_state.current_task_id = task.task_id
        reset_hero_dispatch_timers(hero_state)
        hero_state.travel_end_time = float(now) + float(task.travel_time)
        hero_state.current_position = CAMPAIGN_HOME_BASE_POSITION

    runtime.event_log.append(
        f"Assigned {', '.join(hero_names)} to {task.task_type} ({task.task_id})."
    )
    return True, f"Assigned {', '.join(hero_names)}."


def start_hero_return(
    runtime: CampaignRuntime,
    hero_name: str,
    now: float,
    task,
    return_time_multiplier: float = 1.0,
) -> None:
    hero_state = get_or_create_hero_dispatch_state(runtime, hero_name)

    travel_time = float(getattr(task, "travel_time", 0.0))
    return_time = max(0.0, travel_time * float(return_time_multiplier))

    hero_state.state = HERO_STATE_RETURNING
    hero_state.assigned_task_id = getattr(task, "task_id", None)
    hero_state.current_task_id = getattr(task, "task_id", None)
    reset_hero_dispatch_timers(hero_state)
    hero_state.return_end_time = float(now) + return_time


def start_hero_rest(
    runtime: CampaignRuntime,
    hero_name: str,
    now: float,
    rest_duration: float,
) -> None:
    hero_state = get_or_create_hero_dispatch_state(runtime, hero_name)

    hero_state.state = HERO_STATE_RESTING
    hero_state.assigned_task_id = None
    hero_state.current_task_id = None
    reset_hero_dispatch_timers(hero_state)
    hero_state.rest_end_time = float(now) + max(0.0, float(rest_duration))
    hero_state.current_position = CAMPAIGN_HOME_BASE_POSITION


def release_hero_to_available(runtime: CampaignRuntime, hero_name: str) -> None:
    hero_state = get_or_create_hero_dispatch_state(runtime, hero_name)

    hero_state.state = HERO_STATE_AVAILABLE
    hero_state.assigned_task_id = None
    hero_state.current_task_id = None
    reset_hero_dispatch_timers(hero_state)
    hero_state.current_position = CAMPAIGN_HOME_BASE_POSITION