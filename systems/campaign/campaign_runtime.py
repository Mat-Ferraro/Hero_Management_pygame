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
    TASK_STATE_AWAITING_ACK,
    TASK_STATE_COMPLETED,
    TASK_STATE_EXPIRED,
    TASK_STATE_FAILED,
    TASK_STATE_PENDING,
    TASK_STATE_TRAVELING_TO,
    TASK_STATE_WAITING_FOR_DECISION,
)
from .campaign_models import CampaignDecisionChoice, CampaignDecisionEvent, CampaignRuntime
from .task_dispatch import (
    find_task,
    get_or_create_hero_dispatch_state,
    release_hero_to_available,
    start_hero_rest,
    start_hero_return,
)
from .task_generator import build_linked_runtime_tasks, create_runtime_task
from .task_resolution import resolve_task_outcome_from_chance
from systems.progression.hero_progression import award_training_points_for_outcome


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
    runtime.event_log.append(str(message))


def ensure_hero_states_for_roster(runtime: CampaignRuntime, roster) -> None:
    for hero in roster:
        get_or_create_hero_dispatch_state(runtime, hero.name)


def find_hero_by_name(state, hero_name: str):
    for hero in getattr(state, "roster", []):
        if getattr(hero, "name", None) == hero_name:
            return hero
    return None


def clamp_satisfaction(value: int) -> int:
    return max(0, min(100, int(value)))


def apply_hero_satisfaction_delta(hero, delta: int) -> int:
    if hero is None or not hasattr(hero, "satisfaction"):
        return 0

    old_value = int(getattr(hero, "satisfaction", 50))
    new_value = clamp_satisfaction(old_value + int(delta))
    setattr(hero, "satisfaction", new_value)
    return new_value - old_value


def normalize_decision_choice(choice) -> CampaignDecisionChoice:
    if isinstance(choice, CampaignDecisionChoice):
        return choice

    if isinstance(choice, dict):
        return CampaignDecisionChoice.from_dict(choice)

    return CampaignDecisionChoice(
        id="choice",
        label=str(choice),
    )


def iter_decision_choices(event: CampaignDecisionEvent) -> list[CampaignDecisionChoice]:
    return [normalize_decision_choice(choice) for choice in getattr(event, "choices", []) or []]


def find_decision_choice(event: CampaignDecisionEvent, choice_id: str) -> Optional[CampaignDecisionChoice]:
    choice_id = str(choice_id).strip()
    if not choice_id:
        return None

    for choice in iter_decision_choices(event):
        if choice.id == choice_id:
            return choice

    return None


def apply_choice_reward_modifiers(task, reward_modifiers: dict) -> None:
    if not reward_modifiers:
        return

    gold_multiplier = reward_modifiers.get("gold_multiplier")
    if gold_multiplier is not None:
        task.reward_gold_min = max(0, int(round(float(task.reward_gold_min) * float(gold_multiplier))))
        task.reward_gold_max = max(
            task.reward_gold_min,
            int(round(float(task.reward_gold_max) * float(gold_multiplier))),
        )

    xp_multiplier = reward_modifiers.get("xp_multiplier")
    if xp_multiplier is not None:
        task.reward_xp = max(0, int(round(float(task.reward_xp) * float(xp_multiplier))))

    duration_multiplier = reward_modifiers.get("duration_multiplier")
    if duration_multiplier is not None:
        task.task_duration = max(4.0, float(task.task_duration) * float(duration_multiplier))

    injury_multiplier = reward_modifiers.get("injury_multiplier")
    if injury_multiplier is not None:
        task.reward_modifiers["injury_multiplier"] = float(injury_multiplier)


def spawn_linked_tasks_from_parent(runtime: CampaignRuntime, parent_task, rng: random.Random) -> int:
    spawned = build_linked_runtime_tasks(
        runtime=runtime,
        parent_task=parent_task,
        now=runtime.elapsed_time,
        rng=rng,
    )

    if not spawned:
        return 0

    for task in spawned:
        runtime.active_tasks.append(task)
        log_event(
            runtime,
            f"Follow-up task spawned: {task.task_type} ({task.task_id}) from {parent_task.task_id}.",
        )

    parent_task.linked_tasks = []
    return len(spawned)


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
        existing_tasks=runtime.active_tasks,
    )

    runtime.active_tasks.append(task)
    runtime.total_spawns += 1
    runtime.next_spawn_time = runtime.elapsed_time + DEFAULT_CAMPAIGN_SPAWN_INTERVAL

    log_event(
        runtime,
        f"Task spawned: {task.task_type} ({task.task_id}) | expires at {task.expire_time:.2f}",
    )
    return task.task_id


def maybe_open_decision_for_task(runtime: CampaignRuntime, task, rng: random.Random) -> bool:
    if runtime.open_decision_event is not None:
        return False

    if not bool(getattr(task, "can_trigger_decision", False)):
        return False

    decision_chance = float(getattr(task, "decision_chance", 0.0))
    decision_chance = max(0.0, min(1.0, decision_chance))

    if decision_chance <= 0.0:
        return False

    if rng.random() > decision_chance:
        return False

    raw_choices = list(
        getattr(
            task,
            "decision_choices",
            [
                {"id": "push", "label": "Push forward"},
                {"id": "safe", "label": "Take the safer route"},
            ],
        )
        or []
    )
    normalized_choices = [normalize_decision_choice(choice) for choice in raw_choices]

    runtime.open_decision_event = CampaignDecisionEvent(
        task_id=task.task_id,
        title=getattr(task, "decision_title", "Mid-Mission Decision"),
        description=getattr(
            task,
            "decision_description",
            f"The team on {task.task_type} must choose how to proceed.",
        ),
        choices=normalized_choices,
        event_id=f"{task.task_id}_decision",
        step_index=0,
        total_steps=1,
        source="task",
        branch_flags=dict(getattr(task, "branch_flags", {}) or {}),
    )

    task.state = TASK_STATE_WAITING_FOR_DECISION

    for hero_name in task.assigned_heroes:
        hero_state = get_or_create_hero_dispatch_state(runtime, hero_name)
        hero_state.state = HERO_STATE_AWAITING_DECISION
        hero_state.current_task_id = task.task_id

    runtime.paused = True
    log_event(runtime, f"Decision opened for task {task.task_id}.")
    return True


def begin_task_execution(runtime: CampaignRuntime, task) -> None:
    task.state = TASK_STATE_ACTIVE
    task.started_at = runtime.elapsed_time
    task.active_until = runtime.elapsed_time + float(task.task_duration)

    for hero_name in task.assigned_heroes:
        hero_state = get_or_create_hero_dispatch_state(runtime, hero_name)
        hero_state.state = HERO_STATE_ON_TASK
        hero_state.current_task_id = task.task_id

    log_event(
        runtime,
        f"Task started: {task.task_type} ({task.task_id}) | "
        f"team size={len(task.assigned_heroes)} | completes at {task.active_until:.2f}",
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

    choice = find_decision_choice(event, choice_id)
    if choice is None:
        return "Decision choice not found."

    task.branch_flags.update(dict(choice.branch_flags))
    task.linked_tasks.extend(list(choice.linked_tasks))
    apply_choice_reward_modifiers(task, dict(choice.reward_modifiers))

    if choice.id == "push":
        task.task_duration = max(4.0, float(task.task_duration) * 0.85)
        task.reward_xp = int(float(task.reward_xp) * 1.10)
    elif choice.id == "safe":
        task.task_duration = float(task.task_duration) * 1.10
        task.reward_gold_max = int(float(task.reward_gold_max) * 1.05)

    runtime.open_decision_event = None
    runtime.paused = False

    log_event(runtime, f"Decision on {task.task_id}: {choice.label}.")
    begin_task_execution(runtime, task)
    return f"Resolved decision for {task.task_id}."


def complete_task(runtime: CampaignRuntime, state, task, rng: random.Random) -> None:
    heroes = []
    for hero_name in task.assigned_heroes:
        hero = find_hero_by_name(state, hero_name)
        if hero is not None:
            heroes.append(hero)

    roll_value = rng.random()
    result = resolve_task_outcome_from_chance(task, heroes, roll_value=roll_value)

    task.success_chance = float(result["success_chance"])
    task.coverage_ratio = float(result["fit_score"])
    task.outcome_band = str(result["outcome_band"])
    task.payout_multiplier = float(result["payout_multiplier"])
    task.xp_multiplier = float(result["xp_multiplier"])

    injury_multiplier = float(task.reward_modifiers.get("injury_multiplier", 1.0))
    reward_floor = int(round(float(task.reward_gold_min) * task.payout_multiplier))
    reward_ceiling = int(round(float(task.reward_gold_max) * task.payout_multiplier))
    reward_floor = max(0, reward_floor)
    reward_ceiling = max(reward_floor, reward_ceiling)

    gold_reward = rng.randint(reward_floor, reward_ceiling) if reward_ceiling > 0 else 0
    state.gold += gold_reward

    task.injured_heroes = []
    task.injury_rest_by_hero = {}
    task.satisfaction_delta_by_hero = {}
    task.training_points_by_hero = {}
    task.consequence_summary = []

    injury_profile = result["injury_profile"]
    adjusted_injury_chance = max(0.0, min(1.0, float(injury_profile["injury_chance"]) * injury_multiplier))
    base_satisfaction_delta = int(result["satisfaction_delta"])

    for hero in heroes:
        hero_name = hero.name
        injury_roll = rng.random()

        extra_rest = 0.0
        if injury_roll < adjusted_injury_chance:
            extra_rest = rng.uniform(
                float(injury_profile["extra_rest_min"]),
                float(injury_profile["extra_rest_max"]),
            )
            extra_rest = round(extra_rest, 1)
            task.injured_heroes.append(hero_name)
            task.injury_rest_by_hero[hero_name] = extra_rest

        actual_delta = apply_hero_satisfaction_delta(hero, base_satisfaction_delta)
        task.satisfaction_delta_by_hero[hero_name] = actual_delta

        tp_messages = award_training_points_for_outcome(hero, task.outcome_band)
        if tp_messages:
            awarded = 2 if task.outcome_band == "great_success" else 1
            task.training_points_by_hero[hero_name] = awarded

    task.consequence_summary.append(f"Success chance was {task.success_chance:.0%}.")

    ability_notes = list(result.get("ability_modifiers", {}).get("notes", []))
    for line in ability_notes[:3]:
        task.consequence_summary.append(line)

    if task.branch_flags:
        task.consequence_summary.append(f"Branch flags: {', '.join(sorted(task.branch_flags.keys()))}.")

    if gold_reward > 0:
        task.consequence_summary.append(f"Guild earned {gold_reward}g.")

    if task.injured_heroes:
        for hero_name in task.injured_heroes:
            rest_time = task.injury_rest_by_hero.get(hero_name, 0.0)
            task.consequence_summary.append(f"{hero_name} was injured and needs +{rest_time:.0f}s rest.")
    else:
        task.consequence_summary.append("No injuries reported.")

    for hero_name, delta in task.satisfaction_delta_by_hero.items():
        if delta > 0:
            task.consequence_summary.append(f"{hero_name} gained {delta} satisfaction.")
        elif delta < 0:
            task.consequence_summary.append(f"{hero_name} lost {abs(delta)} satisfaction.")

    for hero_name, amount in task.training_points_by_hero.items():
        if amount > 0:
            task.consequence_summary.append(f"{hero_name} gained {amount} training point(s).")

    task.state = TASK_STATE_AWAITING_ACK
    task.completed_at = runtime.elapsed_time
    task.active_until = None
    task.outcome_summary = (
        f"{task.outcome_band.replace('_', ' ').title()} | "
        f"Chance {task.success_chance:.0%} | Reward {gold_reward}g"
    )

    spawn_linked_tasks_from_parent(runtime, task, rng)

    log_event(
        runtime,
        f"Task resolved: {task.task_type} ({task.task_id}) | "
        f"{task.outcome_summary} | awaiting acknowledgment",
    )

    for summary_line in task.consequence_summary:
        log_event(runtime, f" - {summary_line}")


def acknowledge_completed_task(runtime: CampaignRuntime, task_id: str) -> str:
    task = find_task(runtime, task_id)
    if task is None:
        return "Task not found."

    if task.state != TASK_STATE_AWAITING_ACK:
        return "Task is not awaiting acknowledgment."

    task.state = TASK_STATE_COMPLETED
    task.acknowledged_at = runtime.elapsed_time

    if task.task_id not in runtime.completed_task_ids:
        runtime.completed_task_ids.append(task.task_id)

    for hero_name in task.assigned_heroes:
        start_hero_return(runtime, hero_name, runtime.elapsed_time, task, DEFAULT_RETURN_TIME_MULTIPLIER)

    log_event(runtime, f"Task acknowledged: {task.task_id}. Heroes are returning.")
    return f"Acknowledged {task.task_id}."


def fail_task_and_return_party(runtime: CampaignRuntime, task) -> None:
    task.state = TASK_STATE_FAILED
    task.completed_at = runtime.elapsed_time
    task.active_until = None
    task.outcome_summary = "Failed"

    for hero_name in task.assigned_heroes:
        start_hero_return(runtime, hero_name, runtime.elapsed_time, task, DEFAULT_RETURN_TIME_MULTIPLIER)

    log_event(runtime, f"Task failed: {task.task_type} ({task.task_id}). Heroes are returning.")


def update_pending_task_expirations(runtime: CampaignRuntime) -> None:
    for task in runtime.active_tasks:
        if task.state == TASK_STATE_PENDING and runtime.elapsed_time >= task.expire_time:
            task.state = TASK_STATE_EXPIRED
            if task.task_id not in runtime.expired_task_ids:
                runtime.expired_task_ids.append(task.task_id)
            log_event(runtime, f"Task expired: {task.task_type} ({task.task_id}).")


def update_traveling_tasks(runtime: CampaignRuntime, rng: random.Random) -> None:
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


def update_active_tasks(runtime: CampaignRuntime, state, rng: random.Random) -> None:
    for task in runtime.active_tasks:
        if task.state != TASK_STATE_ACTIVE:
            continue

        if task.active_until is None:
            log_event(runtime, f"WARNING: active task {task.task_id} has no active_until.")
            continue

        if runtime.elapsed_time >= task.active_until:
            complete_task(runtime, state, task, rng)


def update_hero_return_and_rest(runtime: CampaignRuntime) -> None:
    for hero_name, hero_state in runtime.hero_states.items():
        if hero_state.state == HERO_STATE_RETURNING:
            if hero_state.return_end_time is not None and runtime.elapsed_time >= hero_state.return_end_time:
                related_task_id = hero_state.current_task_id or hero_state.assigned_task_id
                related_task = find_task(runtime, related_task_id) if related_task_id else None

                extra_rest = 0.0
                if related_task is not None:
                    extra_rest = float(related_task.injury_rest_by_hero.get(hero_name, 0.0))

                base_rest = float(related_task.rest_duration) if related_task is not None else 14.0
                rest_duration = base_rest + extra_rest

                start_hero_rest(runtime, hero_name, runtime.elapsed_time, rest_duration)

                if extra_rest > 0:
                    log_event(runtime, f"{hero_name} returned home injured and is resting for {rest_duration:.0f}s.")
                else:
                    log_event(runtime, f"{hero_name} returned home and is now resting.")

        elif hero_state.state == HERO_STATE_RESTING:
            if hero_state.rest_end_time is not None and runtime.elapsed_time >= hero_state.rest_end_time:
                release_hero_to_available(runtime, hero_name)
                log_event(runtime, f"{hero_name} finished resting and is available.")


def maybe_spawn_task(runtime: CampaignRuntime, state, rng: random.Random) -> None:
    if runtime.total_spawns >= runtime.max_spawns:
        return

    if runtime.elapsed_time < runtime.next_spawn_time:
        return

    spawn_next_task(runtime, state, rng)


def tick_campaign_runtime(
    runtime: CampaignRuntime,
    state,
    delta_seconds: float,
    rng: random.Random | None = None,
) -> None:
    if runtime is None:
        return

    if not getattr(runtime, "active", False):
        return

    if getattr(runtime, "paused", False):
        return

    if rng is None:
        rng = random.Random()

    ensure_hero_states_for_roster(runtime, getattr(state, "roster", []))

    delta_seconds = max(0.0, float(delta_seconds))
    runtime.elapsed_time += delta_seconds

    maybe_spawn_task(runtime, state, rng)
    update_pending_task_expirations(runtime)
    update_traveling_tasks(runtime, rng)
    update_active_tasks(runtime, state, rng)
    update_hero_return_and_rest(runtime)

    if campaign_should_end(runtime):
        runtime.active = False
        log_event(runtime, "Campaign ended.")