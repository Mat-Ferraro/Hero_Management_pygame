from __future__ import annotations

import random
from typing import Dict, List, Optional

from .campaign_constants import CAMPAIGN_HOME_BASE_POSITION, CAMPAIGN_MAP_HEIGHT, CAMPAIGN_MAP_WIDTH
from .campaign_models import CampaignTask


TASK_ARCHETYPES: List[Dict] = [
    {
        "task_type": "Bandit Raid",
        "difficulty": 1,
        "recommended_power": 55,
        "expire_duration": 26.0,
        "task_duration": 18.0,
        "reward_gold_min": 50,
        "reward_gold_max": 90,
        "reward_xp": 24,
        "preferred_classes": ["Warrior", "Rogue"],
        "decision_chance": 0.10,
        "rest_duration": 12.0,
    },
    {
        "task_type": "Escort Caravan",
        "difficulty": 2,
        "recommended_power": 85,
        "expire_duration": 32.0,
        "task_duration": 24.0,
        "reward_gold_min": 80,
        "reward_gold_max": 140,
        "reward_xp": 36,
        "preferred_classes": ["Warrior", "Cleric"],
        "decision_chance": 0.15,
        "rest_duration": 14.0,
    },
    {
        "task_type": "Monster Hunt",
        "difficulty": 2,
        "recommended_power": 95,
        "expire_duration": 30.0,
        "task_duration": 28.0,
        "reward_gold_min": 90,
        "reward_gold_max": 160,
        "reward_xp": 42,
        "preferred_classes": ["Warrior", "Mage"],
        "decision_chance": 0.18,
        "rest_duration": 15.0,
    },
    {
        "task_type": "Cursed Shrine",
        "difficulty": 3,
        "recommended_power": 125,
        "expire_duration": 36.0,
        "task_duration": 30.0,
        "reward_gold_min": 110,
        "reward_gold_max": 190,
        "reward_xp": 50,
        "preferred_classes": ["Cleric", "Mage"],
        "decision_chance": 0.28,
        "rest_duration": 16.0,
    },
    {
        "task_type": "Village Defense",
        "difficulty": 3,
        "recommended_power": 140,
        "expire_duration": 24.0,
        "task_duration": 34.0,
        "reward_gold_min": 130,
        "reward_gold_max": 220,
        "reward_xp": 58,
        "preferred_classes": ["Warrior", "Cleric", "Rogue"],
        "decision_chance": 0.22,
        "rest_duration": 18.0,
    },
]


def random_task_position(rng: random.Random) -> tuple[int, int]:
    return (
        rng.randint(340, CAMPAIGN_MAP_WIDTH - 120),
        rng.randint(120, CAMPAIGN_MAP_HEIGHT - 120),
    )


def travel_time_from_home(position: tuple[int, int]) -> float:
    home_x, home_y = CAMPAIGN_HOME_BASE_POSITION
    pos_x, pos_y = position
    distance = ((pos_x - home_x) ** 2 + (pos_y - home_y) ** 2) ** 0.5
    return max(6.0, distance / 85.0)


def choose_task_archetype(
    rng: random.Random,
    unlocked_classes: Optional[List[str]] = None,
) -> Dict:
    candidates = list(TASK_ARCHETYPES)

    if unlocked_classes:
        unlocked = set(unlocked_classes)
        filtered = [
            task for task in candidates
            if any(hero_class in unlocked for hero_class in task["preferred_classes"])
        ]
        if filtered:
            candidates = filtered

    return dict(rng.choice(candidates))


def create_runtime_task(
    task_id: str,
    now: float,
    rng: random.Random,
    unlocked_classes: Optional[List[str]] = None,
) -> CampaignTask:
    archetype = choose_task_archetype(rng, unlocked_classes=unlocked_classes)
    map_position = random_task_position(rng)
    travel_time = travel_time_from_home(map_position)

    return CampaignTask(
        task_id=task_id,
        task_type=archetype["task_type"],
        state="pending",
        map_position=map_position,
        spawn_time=now,
        expire_time=now + float(archetype["expire_duration"]),
        travel_time=travel_time,
        task_duration=float(archetype["task_duration"]),
        recommended_power=int(archetype["recommended_power"]),
        preferred_classes=list(archetype["preferred_classes"]),
        difficulty=int(archetype["difficulty"]),
        reward_gold_min=int(archetype["reward_gold_min"]),
        reward_gold_max=int(archetype["reward_gold_max"]),
        reward_xp=int(archetype["reward_xp"]),
        decision_chance=float(archetype["decision_chance"]),
        rest_duration=float(archetype["rest_duration"]),
    )