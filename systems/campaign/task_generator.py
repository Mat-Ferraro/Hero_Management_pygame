from __future__ import annotations

import copy
import math
import random
from typing import Any, Dict, List, Tuple

from .campaign_models import CampaignTask


MAP_POSITIONS: List[Tuple[int, int]] = [
    (440, 240),
    (620, 170),
    (810, 290),
    (1000, 230),
    (1180, 350),
    (890, 470),
    (610, 420),
    (320, 350),
]

MIN_TASK_SEPARATION = 170.0

TASK_TEMPLATES: List[Dict[str, Any]] = [
    {
        "task_type": "Village Defense",
        "difficulty": 2,
        "max_heroes": 3,
        "preferred_classes": ["Warrior", "Cleric"],
        "stat_rules": {
            "might": {"mode": "minimum", "target": 8},
            "guard": {"mode": "minimum", "target": 9},
            "presence": {"mode": "minimum", "target": 5},
        },
        "decision_chance": 0.25,
        "decision_title": "Hold the Line?",
        "decision_description": "The defenders can either commit to a hard stand or pull civilians back first.",
        "decision_choices": [
            {
                "id": "hold_line",
                "label": "Hold the line",
                "description": "Risk more to preserve the village.",
                "branch_flags": {"held_line": True},
                "reward_modifiers": {"gold_multiplier": 1.10, "injury_multiplier": 1.15},
                "tags": ["defense", "high_risk"],
            },
            {
                "id": "evacuate",
                "label": "Evacuate first",
                "description": "Safer, but less rewarding.",
                "branch_flags": {"evacuated_villagers": True},
                "reward_modifiers": {"gold_multiplier": 0.90, "injury_multiplier": 0.90},
                "tags": ["defense", "safe"],
            },
        ],
        "task_tags": ["defense", "civilian", "frontier"],
    },
    {
        "task_type": "Bandit Interception",
        "difficulty": 2,
        "max_heroes": 2,
        "preferred_classes": ["Rogue", "Warrior"],
        "stat_rules": {
            "swift": {"mode": "minimum", "target": 8},
            "wit": {"mode": "minimum", "target": 6},
            "might": {"mode": "minimum", "target": 5},
        },
        "decision_chance": 0.15,
        "decision_title": "Ambush or Pursuit?",
        "decision_description": "The bandits can be cut off now, or tracked to a richer cache.",
        "decision_choices": [
            {
                "id": "ambush_now",
                "label": "Ambush now",
                "description": "Lower risk, cleaner success.",
                "branch_flags": {"bandits_disrupted": True},
                "tags": ["bandits", "safe"],
            },
            {
                "id": "track_hideout",
                "label": "Track the hideout",
                "description": "Higher risk, possible follow-up opportunity.",
                "branch_flags": {"bandit_hideout_found": True},
                "linked_tasks": [{"task_type": "Bandit Hideout Raid"}],
                "reward_modifiers": {"gold_multiplier": 1.10},
                "tags": ["bandits", "chain_seed"],
            },
        ],
        "task_tags": ["bandits", "interception"],
    },
    {
        "task_type": "Ritual Disturbance",
        "difficulty": 3,
        "max_heroes": 3,
        "preferred_classes": ["Cleric", "Mage"],
        "stat_rules": {
            "wit": {"mode": "minimum", "target": 9},
            "presence": {"mode": "minimum", "target": 8},
            "guard": {"mode": "minimum", "target": 5},
        },
        "decision_chance": 0.35,
        "decision_title": "Disrupt or Study?",
        "decision_description": "The ritual energy can be broken immediately or studied for a tactical advantage.",
        "decision_choices": [
            {
                "id": "disrupt",
                "label": "Disrupt the ritual",
                "description": "Safer resolution.",
                "branch_flags": {"ritual_broken": True},
                "reward_modifiers": {"injury_multiplier": 0.90},
                "tags": ["ritual", "safe"],
            },
            {
                "id": "study",
                "label": "Study the ritual",
                "description": "Potentially more rewarding, but dangerous.",
                "branch_flags": {"ritual_studied": True},
                "reward_modifiers": {"xp_multiplier": 1.15, "injury_multiplier": 1.10},
                "linked_tasks": [{"task_type": "Arcane Aftershock"}],
                "tags": ["ritual", "arcane", "chain_seed"],
            },
        ],
        "task_tags": ["ritual", "arcane", "unstable"],
    },
    {
        "task_type": "Supply Escort",
        "difficulty": 1,
        "max_heroes": 2,
        "preferred_classes": ["Warrior", "Cleric"],
        "stat_rules": {
            "guard": {"mode": "minimum", "target": 6},
            "presence": {"mode": "minimum", "target": 4},
        },
        "decision_chance": 0.10,
        "task_tags": ["escort", "logistics"],
    },
    {
        "task_type": "Scout the Ruins",
        "difficulty": 2,
        "max_heroes": 2,
        "preferred_classes": ["Rogue", "Mage"],
        "stat_rules": {
            "swift": {"mode": "minimum", "target": 7},
            "wit": {"mode": "minimum", "target": 7},
            "guard": {"mode": "maximum", "target": 10},
        },
        "decision_chance": 0.20,
        "decision_title": "Go Deep?",
        "decision_description": "The scouts can stop with surface intel or push deeper into the ruins.",
        "decision_choices": [
            {
                "id": "surface_only",
                "label": "Take the surface intel",
                "description": "Reliable and quick.",
                "branch_flags": {"ruins_scouted": True},
                "tags": ["scouting", "safe"],
            },
            {
                "id": "push_deeper",
                "label": "Push deeper",
                "description": "Risk more for better intelligence.",
                "branch_flags": {"deep_ruin_path_found": True},
                "linked_tasks": [{"task_type": "Ruin Excavation"}],
                "reward_modifiers": {"xp_multiplier": 1.10},
                "tags": ["scouting", "chain_seed"],
            },
        ],
        "task_tags": ["scouting", "ruins"],
    },
    {
        "task_type": "Public Festival Security",
        "difficulty": 1,
        "max_heroes": 2,
        "preferred_classes": ["Warrior", "Cleric", "Rogue"],
        "stat_rules": {
            "presence": {"mode": "minimum", "target": 6},
            "guard": {"mode": "minimum", "target": 5},
            "swift": {"mode": "range", "min": 3, "max": 8},
        },
        "decision_chance": 0.12,
        "task_tags": ["civilian", "security", "urban"],
    },
]

TASK_TYPE_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "Bandit Hideout Raid": {
        "difficulty": 3,
        "max_heroes": 3,
        "preferred_classes": ["Rogue", "Warrior"],
        "stat_rules": {
            "swift": {"mode": "minimum", "target": 8},
            "might": {"mode": "minimum", "target": 8},
            "wit": {"mode": "minimum", "target": 6},
        },
        "decision_chance": 0.25,
        "task_tags": ["bandits", "raid", "chain"],
    },
    "Arcane Aftershock": {
        "difficulty": 3,
        "max_heroes": 3,
        "preferred_classes": ["Mage", "Cleric"],
        "stat_rules": {
            "wit": {"mode": "minimum", "target": 9},
            "presence": {"mode": "minimum", "target": 7},
            "guard": {"mode": "minimum", "target": 5},
        },
        "decision_chance": 0.20,
        "task_tags": ["arcane", "chain", "unstable"],
    },
    "Ruin Excavation": {
        "difficulty": 3,
        "max_heroes": 3,
        "preferred_classes": ["Rogue", "Mage", "Warrior"],
        "stat_rules": {
            "wit": {"mode": "minimum", "target": 8},
            "swift": {"mode": "minimum", "target": 6},
            "guard": {"mode": "minimum", "target": 6},
        },
        "decision_chance": 0.18,
        "task_tags": ["ruins", "chain", "exploration"],
    },
}


def _distance(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _normalize_stat_rule(rule: Dict[str, Any] | None) -> Dict[str, Any]:
    if not rule:
        return {"mode": "minimum", "target": 0}

    mode = str(rule.get("mode", "minimum")).lower()

    if mode == "range":
        min_value = max(0, int(rule.get("min", 0)))
        max_value = max(min_value, int(rule.get("max", min_value)))
        return {"mode": "range", "min": min_value, "max": max_value}

    if mode == "maximum":
        return {"mode": "maximum", "target": max(0, int(rule.get("target", 0)))}

    return {"mode": "minimum", "target": max(0, int(rule.get("target", 0)))}


def _normalize_stat_rules(stat_rules: Dict[str, Dict[str, Any]] | None) -> Dict[str, Dict[str, Any]]:
    normalized: Dict[str, Dict[str, Any]] = {}
    for stat_name, rule in dict(stat_rules or {}).items():
        normalized[str(stat_name)] = _normalize_stat_rule(rule)
    return normalized


def _representative_required_stats(stat_rules: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    representative: Dict[str, int] = {}

    for stat_name, rule in dict(stat_rules or {}).items():
        mode = str(rule.get("mode", "minimum")).lower()

        if mode == "minimum":
            representative[stat_name] = max(0, int(rule.get("target", 0)))
        elif mode == "range":
            min_value = max(0, int(rule.get("min", 0)))
            max_value = max(min_value, int(rule.get("max", min_value)))
            representative[stat_name] = int(round((min_value + max_value) / 2))
        elif mode == "maximum":
            representative[stat_name] = max(0, int(rule.get("target", 0)))

    return representative


def _task_reward_values(difficulty: int, rng: random.Random) -> tuple[int, int, int]:
    gold_min = 50 + (difficulty * 25) + rng.randint(0, 30)
    gold_max = gold_min + 60 + (difficulty * 30) + rng.randint(0, 50)
    xp_reward = 18 + (difficulty * 10) + rng.randint(0, 8)
    return gold_min, gold_max, xp_reward


def _task_timing_values(difficulty: int, rng: random.Random) -> tuple[float, float, float, float]:
    expire_time_offset = rng.uniform(18.0, 28.0)
    travel_time = rng.uniform(6.0, 12.0)
    task_duration = rng.uniform(24.0, 40.0)
    rest_duration = 12.0 + (difficulty * 4.0)
    return expire_time_offset, travel_time, task_duration, rest_duration


def choose_task_position(rng: random.Random, existing_tasks) -> Tuple[int, int]:
    occupied_positions = [
        tuple(task.map_position)
        for task in existing_tasks
        if getattr(task, "state", "") not in {"completed", "failed", "expired"}
    ]

    shuffled_positions = list(MAP_POSITIONS)
    rng.shuffle(shuffled_positions)

    for candidate in shuffled_positions:
        if all(_distance(candidate, occupied) >= MIN_TASK_SEPARATION for occupied in occupied_positions):
            return candidate

    for candidate in shuffled_positions:
        if candidate not in occupied_positions:
            return candidate

    return rng.choice(shuffled_positions)


def _choose_template(rng: random.Random) -> Dict[str, Any]:
    return copy.deepcopy(rng.choice(TASK_TEMPLATES))


def _apply_task_type_override(template: Dict[str, Any]) -> Dict[str, Any]:
    task_type = str(template.get("task_type", "")).strip()
    override = TASK_TYPE_OVERRIDES.get(task_type)
    if not override:
        return template

    merged = copy.deepcopy(template)
    for key, value in override.items():
        merged[key] = copy.deepcopy(value)
    return merged


def _next_chain_task_id(runtime) -> str:
    existing_ids = {getattr(task, "task_id", "") for task in getattr(runtime, "active_tasks", [])}
    index = 1

    while True:
        candidate = f"chain_{index:03d}"
        if candidate not in existing_ids:
            return candidate
        index += 1


def build_linked_runtime_tasks(
    runtime,
    parent_task: CampaignTask,
    now: float,
    rng: random.Random,
) -> List[CampaignTask]:
    spawned_tasks: List[CampaignTask] = []

    raw_linked_tasks = list(getattr(parent_task, "linked_tasks", []) or [])
    if not raw_linked_tasks:
        return spawned_tasks

    chain_id = getattr(parent_task, "chain_id", None) or parent_task.task_id

    for linked_task_data in raw_linked_tasks:
        if not isinstance(linked_task_data, dict):
            continue

        template = build_task_template_from_linked_task(linked_task_data)
        new_task_id = _next_chain_task_id(runtime)

        task = create_runtime_task(
            task_id=new_task_id,
            now=now,
            rng=rng,
            existing_tasks=getattr(runtime, "active_tasks", []),
            template=template,
            origin_task_id=parent_task.task_id,
            chain_id=chain_id,
        )
        spawned_tasks.append(task)

    return spawned_tasks


def build_task_template_from_linked_task(linked_task_data: Dict[str, Any]) -> Dict[str, Any]:
    task_type = str(linked_task_data.get("task_type", "Follow-up Task")).strip() or "Follow-up Task"

    base_template: Dict[str, Any] = {
        "task_type": task_type,
        "difficulty": int(linked_task_data.get("difficulty", 2)),
        "max_heroes": int(linked_task_data.get("max_heroes", 2)),
        "preferred_classes": list(linked_task_data.get("preferred_classes", []) or []),
        "stat_rules": _normalize_stat_rules(linked_task_data.get("stat_rules", {})),
        "decision_chance": float(linked_task_data.get("decision_chance", 0.0)),
        "decision_title": str(linked_task_data.get("decision_title", "")),
        "decision_description": str(linked_task_data.get("decision_description", "")),
        "decision_choices": list(linked_task_data.get("decision_choices", []) or []),
        "task_tags": list(linked_task_data.get("task_tags", []) or ["chain"]),
        "linked_tasks": list(linked_task_data.get("linked_tasks", []) or []),
    }

    return _apply_task_type_override(base_template)


def create_runtime_task(
    task_id: str,
    now: float,
    rng: random.Random,
    unlocked_classes=None,
    existing_tasks=None,
    template: Dict[str, Any] | None = None,
    origin_task_id: str | None = None,
    chain_id: str | None = None,
) -> CampaignTask:
    if template is None:
        template = _choose_template(rng)
    else:
        template = copy.deepcopy(template)

    template = _apply_task_type_override(template)

    difficulty = max(1, int(template.get("difficulty", 1)))
    max_heroes = min(3, max(1, int(template.get("max_heroes", 1))))

    expire_offset, travel_time, task_duration, rest_duration = _task_timing_values(difficulty, rng)
    reward_gold_min, reward_gold_max, reward_xp = _task_reward_values(difficulty, rng)

    stat_rules = _normalize_stat_rules(template.get("stat_rules", {}))
    required_stats = _representative_required_stats(stat_rules)
    recommended_power = max(1, sum(required_stats.values()))

    map_position = choose_task_position(rng, existing_tasks or [])

    decision_choices = list(template.get("decision_choices", []) or [])
    can_trigger_decision = bool(decision_choices) or float(template.get("decision_chance", 0.0)) > 0.0

    task_tags = list(template.get("task_tags", []) or [])
    linked_tasks = list(template.get("linked_tasks", []) or [])

    return CampaignTask(
        task_id=task_id,
        task_type=str(template.get("task_type", "Unknown Task")),
        state="pending",
        map_position=map_position,
        spawn_time=float(now),
        expire_time=float(now) + expire_offset,
        travel_time=travel_time,
        task_duration=task_duration,
        recommended_power=recommended_power,
        required_stats=required_stats,
        stat_rules=stat_rules,
        max_heroes=max_heroes,
        preferred_classes=list(template.get("preferred_classes", []) or []),
        assigned_heroes=[],
        difficulty=difficulty,
        reward_gold_min=reward_gold_min,
        reward_gold_max=reward_gold_max,
        reward_xp=reward_xp,
        rest_duration=rest_duration,
        can_trigger_decision=can_trigger_decision,
        decision_chance=float(template.get("decision_chance", 0.0)),
        decision_title=str(template.get("decision_title", "")),
        decision_description=str(template.get("decision_description", "")),
        decision_choices=decision_choices,
        linked_tasks=linked_tasks,
        task_tags=task_tags,
        origin_task_id=origin_task_id,
        chain_id=chain_id,
    )