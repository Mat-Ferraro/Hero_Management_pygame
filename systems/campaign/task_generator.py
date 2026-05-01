from __future__ import annotations

import copy
import random

from .campaign_models import CampaignTask

MAP_POSITIONS = [
    (440, 240),
    (620, 170),
    (810, 290),
    (1000, 230),
    (1180, 350),
    (890, 470),
    (610, 420),
    (320, 350),
]

TASK_TEMPLATES = [
    {
        "task_type": "Village Defense",
        "difficulty": 2,
        "max_heroes": 3,
        "preferred_classes": ["Warrior", "Cleric"],
        "decision_chance": 0.12,
        "stat_rules": {
            "might": {"mode": "minimum", "target": 5},
            "guard": {"mode": "minimum", "target": 6},
            "wit": {"mode": "minimum", "target": 2},
            "presence": {"mode": "minimum", "target": 2},
            "swift": {"mode": "range", "min": 2, "max": 5},
        },
    },
    {
        "task_type": "Monster Hunt",
        "difficulty": 3,
        "max_heroes": 3,
        "preferred_classes": ["Warrior", "Rogue"],
        "decision_chance": 0.18,
        "stat_rules": {
            "might": {"mode": "minimum", "target": 6},
            "guard": {"mode": "minimum", "target": 4},
            "wit": {"mode": "range", "min": 1, "max": 4},
            "presence": {"mode": "maximum", "target": 4},
            "swift": {"mode": "minimum", "target": 4},
        },
    },
    {
        "task_type": "Cursed Shrine",
        "difficulty": 3,
        "max_heroes": 3,
        "preferred_classes": ["Cleric", "Mage"],
        "decision_chance": 0.25,
        "stat_rules": {
            "might": {"mode": "maximum", "target": 5},
            "guard": {"mode": "range", "min": 2, "max": 5},
            "wit": {"mode": "minimum", "target": 5},
            "presence": {"mode": "minimum", "target": 4},
            "swift": {"mode": "minimum", "target": 2},
        },
    },
    {
        "task_type": "Escort Caravan",
        "difficulty": 2,
        "max_heroes": 3,
        "preferred_classes": ["Warrior", "Cleric", "Rogue"],
        "decision_chance": 0.15,
        "stat_rules": {
            "might": {"mode": "range", "min": 2, "max": 5},
            "guard": {"mode": "minimum", "target": 4},
            "wit": {"mode": "range", "min": 2, "max": 5},
            "presence": {"mode": "minimum", "target": 3},
            "swift": {"mode": "minimum", "target": 3},
        },
    },
    {
        "task_type": "Apprehend Art Thieves",
        "difficulty": 3,
        "max_heroes": 3,
        "preferred_classes": ["Rogue", "Mage"],
        "decision_chance": 0.20,
        "stat_rules": {
            "might": {"mode": "maximum", "target": 4},
            "guard": {"mode": "maximum", "target": 4},
            "wit": {"mode": "minimum", "target": 6},
            "presence": {"mode": "range", "min": 2, "max": 5},
            "swift": {"mode": "minimum", "target": 5},
        },
    },
    {
        "task_type": "Diplomatic Escort",
        "difficulty": 2,
        "max_heroes": 3,
        "preferred_classes": ["Cleric", "Warrior", "Mage"],
        "decision_chance": 0.10,
        "stat_rules": {
            "might": {"mode": "maximum", "target": 4},
            "guard": {"mode": "range", "min": 3, "max": 5},
            "wit": {"mode": "range", "min": 2, "max": 5},
            "presence": {"mode": "minimum", "target": 5},
            "swift": {"mode": "range", "min": 2, "max": 5},
        },
    },
    {
        "task_type": "Scout Ruins",
        "difficulty": 2,
        "max_heroes": 2,
        "preferred_classes": ["Rogue", "Mage"],
        "decision_chance": 0.12,
        "stat_rules": {
            "might": {"mode": "maximum", "target": 3},
            "guard": {"mode": "maximum", "target": 4},
            "wit": {"mode": "minimum", "target": 4},
            "presence": {"mode": "maximum", "target": 4},
            "swift": {"mode": "minimum", "target": 5},
        },
    },
]


def _representative_required_stats(stat_rules: dict) -> dict:
    required = {}
    for stat_name, rule in stat_rules.items():
        mode = str(rule.get("mode", "minimum")).lower()

        if mode == "minimum":
            required[stat_name] = int(rule.get("target", 0))
        elif mode == "range":
            min_value = int(rule.get("min", 0))
            max_value = int(rule.get("max", min_value))
            required[stat_name] = max(min_value, max_value)
        elif mode == "maximum":
            required[stat_name] = int(rule.get("target", 0))
        else:
            required[stat_name] = int(rule.get("target", 0))
    return required


def _task_reward_values(difficulty: int, rng: random.Random) -> tuple[int, int, int]:
    gold_min = 50 + (difficulty * 25) + rng.randint(0, 30)
    gold_max = gold_min + 60 + (difficulty * 30) + rng.randint(0, 50)
    xp_reward = 18 + (difficulty * 10) + rng.randint(0, 8)
    return gold_min, gold_max, xp_reward


def create_runtime_task(task_id: str, now: float, rng: random.Random, unlocked_classes=None) -> CampaignTask:
    template = copy.deepcopy(rng.choice(TASK_TEMPLATES))

    difficulty = max(1, int(template.get("difficulty", 1)))
    max_heroes = min(3, max(1, int(template.get("max_heroes", 1))))

    expire_time = now + rng.uniform(18.0, 28.0)
    travel_time = rng.uniform(6.0, 12.0)
    task_duration = rng.uniform(24.0, 40.0)
    rest_duration = 12.0 + (difficulty * 4.0)

    reward_gold_min, reward_gold_max, reward_xp = _task_reward_values(difficulty, rng)

    stat_rules = dict(template.get("stat_rules", {}))
    required_stats = _representative_required_stats(stat_rules)
    recommended_power = sum(required_stats.values())

    return CampaignTask(
        task_id=task_id,
        task_type=str(template["task_type"]),
        state="pending",
        map_position=rng.choice(MAP_POSITIONS),
        spawn_time=now,
        expire_time=expire_time,
        travel_time=travel_time,
        task_duration=task_duration,
        recommended_power=recommended_power,
        required_stats=required_stats,
        stat_rules=stat_rules,
        max_heroes=max_heroes,
        preferred_classes=list(template.get("preferred_classes", [])),
        assigned_heroes=[],
        difficulty=difficulty,
        reward_gold_min=reward_gold_min,
        reward_gold_max=reward_gold_max,
        reward_xp=reward_xp,
        decision_chance=float(template.get("decision_chance", 0.0)),
        rest_duration=rest_duration,
    )