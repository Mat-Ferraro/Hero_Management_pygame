from __future__ import annotations

import random
from typing import Optional

from .campaign_constants import (
    DEFAULT_CAMPAIGN_INITIAL_SPAWN_DELAY,
    DEFAULT_CAMPAIGN_MAX_SPAWNS,
    DEFAULT_CAMPAIGN_SPAWN_INTERVAL,
    DEFAULT_RETURN_TIME_MULTIPLIER,
    HERO_STATE_AWAITING_DECISION,
    HERO_STATE_ON_TASK,
    HERO_STATE_RESTING,
    HERO_STATE_RETURNING,
    HERO_STATE_TRAVELING,
    TASK_STATE_ACTIVE,
    TASK_STATE_COMPLETED,
    TASK_STATE_EXPIRED,
    TASK_STATE_FAILED,
    TASK_STATE_PENDING,
    TASK_STATE_TRAVELING_TO,
    TASK_STATE_WAITING_FOR_DECISION,
)
from .campaign_models import CampaignDecisionEvent, CampaignRuntime
from .task_dispatch import (
    find_task,
    get_or_create_hero_dispatch_state,
    release_hero_to_available,
    start_hero_rest,
    start_hero_return,
)
from .task_generator import create_runtime_task


def create_campaign_runtime(
    max_spawns: int = DEFAULT_CAMPAIGN_MAX_SPAWNS,
    initial_spawn_delay: float = DEFAULT_CAMPAIGN_INITIAL_SPAWN_DELAY,
) -> CampaignRuntime:
    return CampaignRuntime(
        active=True,
        paused=False,
        elapsed_time=0.0,
        total_spawns=0,
        max_spawns=max_spawns,
        next_spawn_time=initial_spawn_delay,
        active_tasks=[],
        hero_states={},
        open_decision_event=None,
        event_log=["Campaign started."],
        completed_task_ids=[],
        expired_task_ids=[],
    )


def log_event(runtime: CampaignRuntime, message: str) -> None:
    runtime.event_log.append(message)
    print(message)


def ensure_hero_states_for_roster(runtime: CampaignRuntime, roster) -> None:
    for hero in roster:
        get_or_create_hero_dispatch_state(runtime, hero.name)


def runtime_has_live_content(runtime: CampaignRuntime) -> bool:
    if runtime.open_decision_event is not None:
        return True

    if any(not task.is_terminal() for task in runtime.active_tasks):
        return True

    if any(
        state.state in {
            HERO_STATE_TRAVELING,
            HERO_STATE_ON_TASK,
            HERO_STATE_AWAITING_DECISION,
            HERO_STATE_RETURNING,
            HERO_STATE_RESTING,
        }
        for state in runtime.hero_states.values()
    ):
        return True

    return False


def campaign_should_end(runtime: CampaignRuntime) -> bool:
    if runtime.total_spawns < runtime.max_spawns:
        return False
    return not runtime_has_live_content(runtime)


def spawn_next_task(runtime: CampaignRuntime, state, rng: random.Random) -> Optional[str]:
    if runtime.total_spawns >= runtime.max_spawns:
        return None

    task_id = f"task_{runtime.total_spawns + 1:03d}"
    task = create_runtime_task(
        task_id=task_id,
        now=runtime.elapsed_time,
        rng=rng,
        unlocked_classes=list(getattr(state.guild_upgrades, "unlocked_classes", [])),
    )

    runtime.active_tasks.append(task)
    runtime.total_spawns += 1
    runtime.next_spawn_time = runtime.elapsed_time + DEFAULT_CAMPAIGN_SPAWN_INTERVAL

    log_event(
        runtime,
        f"New task spawned: {task.task_type} ({task.task_id}) | "
        f"duration={task.task_duration:.1f}s | expire={task.expire_time:.1f}",
    )
    return task_id


def maybe_open_decision_for_task(runtime: CampaignRuntime, task, rng: random.Random) -> bool:
    if task.decision_chance <= 0:
        return False

    if rng.random() > task.decision_chance:
        return False

    task.state = TASK_STATE_WAITING_FOR_DECISION
    runtime.paused = True

    runtime.open_decision_event = CampaignDecisionEvent(
        event_id=f"decision_{task.task_id}",
        task_id=task.task_id,
        title=f"{task.task_type} Decision",
        description="The mission hit a complication and needs player input.",
        choices=[
            {"id": "push", "label": "Push forward"},
            {"id": "safe", "label": "Take the safer route"},
        ],
    )

    for hero_name in task.assigned_heroes:
        hero_state = get_or_create_hero_dispatch_state(runtime, hero_name)
        hero_state.state = HERO_STATE_AWAITING_DECISION
        hero_state.travel_end_time = None
        hero_state.task_end_time = None
        hero_state.return_end_time = None

    log_event(runtime, f"Decision opened for {task.task_id}.")
    return True


def begin_task_execution(runtime: CampaignRuntime, task) -> None:
    task.state = TASK_STATE_ACTIVE
    task.started_at = runtime.elapsed_time
    task.active_until = runtime.elapsed_time + task.task_duration

    for hero_name in task.assigned_heroes:
        hero_state = get_or_create_hero_dispatch_state(runtime, hero_name)
        hero_state.state = HERO_STATE_ON_TASK
        hero_state.travel_end_time = None
        hero_state.task_end_time = None
        hero_state.return_end_time = None
        hero_state.rest_end_time = None
        hero_state.current_position = task.map_position

    log_event(
        runtime,
        f"Task started: {task.task_type} ({task.task_id}) | "
        f"now={runtime.elapsed_time:.2f} | duration={task.task_duration:.2f} | "
        f"active_until={task.active_until:.2f}",
    )

    if task.active_until <= runtime.elapsed_time:
        log_event(
            runtime,
            f"WARNING: task {task.task_id} started with invalid active_until "
            f"({task.active_until:.2f} <= {runtime.elapsed_time:.2f})",
        )


def resolve_open_decision(runtime: CampaignRuntime, choice_id: str) -> str:
    event = runtime.open_decision_event
    if event is None:
        return "No open decision event."

    task = find_task(runtime, event.task_id)
    if task is None:
        runtime.open_decision_event = None
        runtime.paused = False
        return "Decision cleared; task no longer exists."

    if choice_id == "push":
        task.task_duration = max(4.0, task.task_duration * 0.85)
        task.reward_xp = int(task.reward_xp * 1.10)
        log_event(runtime, f"Decision on {task.task_id}: pushed forward.")
    else:
        task.task_duration = task.task_duration * 1.10
        task.reward_gold_max = int(task.reward_gold_max * 1.05)
        log_event(runtime, f"Decision on {task.task_id}: safer route.")

    runtime.open_decision_event = None
    runtime.paused = False
    begin_task_execution(runtime, task)
    return f"Resolved decision for {task.task_id}."


def complete_task(runtime: CampaignRuntime, state, task, rng: random.Random) -> None:
    log_event(
        runtime,
        f"Completing task: {task.task_type} ({task.task_id}) | "
        f"now={runtime.elapsed_time:.2f} | active_until={task.active_until}",
    )

    task.state = TASK_STATE_COMPLETED
    task.completed_at = runtime.elapsed_time
    task.active_until = None
    runtime.completed_task_ids.append(task.task_id)

    gold_reward = rng.randint(task.reward_gold_min, task.reward_gold_max)
    state.gold += gold_reward

    log_event(
        runtime,
        f"Task completed: {task.task_type} ({task.task_id}) for {gold_reward}g.",
    )

    return_time = task.travel_time * DEFAULT_RETURN_TIME_MULTIPLIER
    for hero_name in task.assigned_heroes:
        start_hero_return(
            runtime=runtime,
            hero_name=hero_name,
            task_id=task.task_id,
            now=runtime.elapsed_time,
            return_time=return_time,
        )


def fail_task(runtime: CampaignRuntime, task, reason: str) -> None:
    task.state = TASK_STATE_FAILED
    task.failed_reason = reason
    task.active_until = None

    log_event(runtime, f"Task failed: {task.task_id} ({reason}).")

    for hero_name in task.assigned_heroes:
        start_hero_return(
            runtime=runtime,
            hero_name=hero_name,
            task_id=task.task_id,
            now=runtime.elapsed_time,
            return_time=task.travel_time,
        )


def should_task_fail_after_execution(runtime: CampaignRuntime, state, task, rng: random.Random) -> bool:
    """
    Placeholder MVP failure logic.
    Right now tasks usually succeed. Later this should use hero power,
    preferred class matches, injuries, multi-hero assignment, etc.
    """
    return False


def tick_campaign_runtime(runtime: CampaignRuntime, state, delta_time: float, rng: Optional[random.Random] = None) -> None:
    if not runtime.active:
        return

    ensure_hero_states_for_roster(runtime, state.roster)

    if runtime.paused:
        return

    if rng is None:
        rng = random.Random()

    runtime.elapsed_time += max(0.0, float(delta_time))

    if runtime.total_spawns < runtime.max_spawns and runtime.elapsed_time >= runtime.next_spawn_time:
        spawn_next_task(runtime, state, rng)

    # Only completely unassigned tasks can expire.
    for task in runtime.active_tasks:
        if task.state == TASK_STATE_PENDING and runtime.elapsed_time >= task.expire_time:
            task.state = TASK_STATE_EXPIRED
            runtime.expired_task_ids.append(task.task_id)
            log_event(runtime, f"Task expired: {task.task_type} ({task.task_id}).")

    # Assigned tasks no longer fail for arriving after the original pending timer.
    # Once assigned, they are committed and should execute normally after arrival.
    for task in runtime.active_tasks:
        if task.state != TASK_STATE_TRAVELING_TO:
            continue

        all_arrived = True

        for hero_name in task.assigned_heroes:
            hero_state = get_or_create_hero_dispatch_state(runtime, hero_name)

            if hero_state.travel_end_time is None or runtime.elapsed_time < hero_state.travel_end_time:
                all_arrived = False
                break

        if not all_arrived:
            continue

        if maybe_open_decision_for_task(runtime, task, rng):
            continue

        begin_task_execution(runtime, task)

    for task in runtime.active_tasks:
        if task.state != TASK_STATE_ACTIVE:
            continue

        if task.active_until is None:
            log_event(runtime, f"WARNING: active task {task.task_id} has no active_until.")
            continue

        if runtime.elapsed_time >= task.active_until:
            if should_task_fail_after_execution(runtime, state, task, rng):
                fail_task(runtime, task, "task execution failed")
            else:
                complete_task(runtime, state, task, rng)

    for hero_name, hero_state in runtime.hero_states.items():
        if hero_state.state == HERO_STATE_RETURNING:
            if hero_state.return_end_time is not None and runtime.elapsed_time >= hero_state.return_end_time:
                related_task = find_task(runtime, hero_state.assigned_task_id) if hero_state.assigned_task_id else None
                rest_duration = related_task.rest_duration if related_task else 14.0
                start_hero_rest(runtime, hero_name, runtime.elapsed_time, rest_duration)
                log_event(runtime, f"{hero_name} returned home and is now resting.")

        elif hero_state.state == HERO_STATE_RESTING:
            if hero_state.rest_end_time is not None and runtime.elapsed_time >= hero_state.rest_end_time:
                release_hero_to_available(runtime, hero_name)
                log_event(runtime, f"{hero_name} finished resting and is available.")

    if campaign_should_end(runtime):
        runtime.active = False
        log_event(runtime, "Campaign ended.")