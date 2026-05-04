from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class HeroDispatchState:
    hero_name: str
    state: str = "available"
    assigned_task_id: Optional[str] = None
    travel_end_time: Optional[float] = None
    task_end_time: Optional[float] = None
    return_end_time: Optional[float] = None
    rest_end_time: Optional[float] = None
    current_position: Optional[Tuple[int, int]] = None

    def to_dict(self) -> Dict:
        return {
            "hero_name": self.hero_name,
            "state": self.state,
            "assigned_task_id": self.assigned_task_id,
            "travel_end_time": self.travel_end_time,
            "task_end_time": self.task_end_time,
            "return_end_time": self.return_end_time,
            "rest_end_time": self.rest_end_time,
            "current_position": list(self.current_position) if self.current_position else None,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "HeroDispatchState":
        position = data.get("current_position")
        return cls(
            hero_name=str(data.get("hero_name", "")),
            state=str(data.get("state", "available")),
            assigned_task_id=data.get("assigned_task_id"),
            travel_end_time=data.get("travel_end_time"),
            task_end_time=data.get("task_end_time"),
            return_end_time=data.get("return_end_time"),
            rest_end_time=data.get("rest_end_time"),
            current_position=tuple(position) if position else None,
        )


@dataclass
class CampaignTask:
    task_id: str
    task_type: str
    state: str
    map_position: Tuple[int, int]
    spawn_time: float
    expire_time: float
    travel_time: float
    task_duration: float
    recommended_power: int
    required_stats: Dict[str, int] = field(default_factory=dict)
    stat_rules: Dict[str, Dict] = field(default_factory=dict)
    max_heroes: int = 1
    preferred_classes: List[str] = field(default_factory=list)
    assigned_heroes: List[str] = field(default_factory=list)
    difficulty: int = 1
    reward_gold_min: int = 0
    reward_gold_max: int = 0
    reward_xp: int = 0
    decision_chance: float = 0.0
    rest_duration: float = 14.0
    started_at: Optional[float] = None
    active_until: Optional[float] = None
    completed_at: Optional[float] = None
    acknowledged_at: Optional[float] = None
    failed_reason: str = ""
    outcome_band: str = ""
    success_chance: float = 0.0
    coverage_ratio: float = 0.0
    payout_multiplier: float = 1.0
    xp_multiplier: float = 1.0
    outcome_summary: str = ""
    injured_heroes: List[str] = field(default_factory=list)
    injury_rest_by_hero: Dict[str, float] = field(default_factory=dict)
    satisfaction_delta_by_hero: Dict[str, int] = field(default_factory=dict)
    training_points_by_hero: Dict[str, int] = field(default_factory=dict)
    consequence_summary: List[str] = field(default_factory=list)

    def is_terminal(self) -> bool:
        return self.state in {"completed", "failed", "expired"}

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "state": self.state,
            "map_position": list(self.map_position),
            "spawn_time": self.spawn_time,
            "expire_time": self.expire_time,
            "travel_time": self.travel_time,
            "task_duration": self.task_duration,
            "recommended_power": self.recommended_power,
            "required_stats": dict(self.required_stats),
            "stat_rules": dict(self.stat_rules),
            "max_heroes": self.max_heroes,
            "preferred_classes": list(self.preferred_classes),
            "assigned_heroes": list(self.assigned_heroes),
            "difficulty": self.difficulty,
            "reward_gold_min": self.reward_gold_min,
            "reward_gold_max": self.reward_gold_max,
            "reward_xp": self.reward_xp,
            "decision_chance": self.decision_chance,
            "rest_duration": self.rest_duration,
            "started_at": self.started_at,
            "active_until": self.active_until,
            "completed_at": self.completed_at,
            "acknowledged_at": self.acknowledged_at,
            "failed_reason": self.failed_reason,
            "outcome_band": self.outcome_band,
            "success_chance": self.success_chance,
            "coverage_ratio": self.coverage_ratio,
            "payout_multiplier": self.payout_multiplier,
            "xp_multiplier": self.xp_multiplier,
            "outcome_summary": self.outcome_summary,
            "injured_heroes": list(self.injured_heroes),
            "injury_rest_by_hero": dict(self.injury_rest_by_hero),
            "satisfaction_delta_by_hero": dict(self.satisfaction_delta_by_hero),
            "training_points_by_hero": dict(self.training_points_by_hero),
            "consequence_summary": list(self.consequence_summary),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CampaignTask":
        return cls(
            task_id=str(data["task_id"]),
            task_type=str(data["task_type"]),
            state=str(data["state"]),
            map_position=tuple(data["map_position"]),
            spawn_time=float(data["spawn_time"]),
            expire_time=float(data["expire_time"]),
            travel_time=float(data["travel_time"]),
            task_duration=float(data["task_duration"]),
            recommended_power=int(data["recommended_power"]),
            required_stats=dict(data.get("required_stats", {})),
            stat_rules=dict(data.get("stat_rules", {})),
            max_heroes=int(data.get("max_heroes", 1)),
            preferred_classes=list(data.get("preferred_classes", [])),
            assigned_heroes=list(data.get("assigned_heroes", [])),
            difficulty=int(data.get("difficulty", 1)),
            reward_gold_min=int(data.get("reward_gold_min", 0)),
            reward_gold_max=int(data.get("reward_gold_max", 0)),
            reward_xp=int(data.get("reward_xp", 0)),
            decision_chance=float(data.get("decision_chance", 0.0)),
            rest_duration=float(data.get("rest_duration", 14.0)),
            started_at=data.get("started_at"),
            active_until=data.get("active_until"),
            completed_at=data.get("completed_at"),
            acknowledged_at=data.get("acknowledged_at"),
            failed_reason=str(data.get("failed_reason", "")),
            outcome_band=str(data.get("outcome_band", "")),
            success_chance=float(data.get("success_chance", 0.0)),
            coverage_ratio=float(data.get("coverage_ratio", 0.0)),
            payout_multiplier=float(data.get("payout_multiplier", 1.0)),
            xp_multiplier=float(data.get("xp_multiplier", 1.0)),
            outcome_summary=str(data.get("outcome_summary", "")),
            injured_heroes=list(data.get("injured_heroes", [])),
            injury_rest_by_hero={str(k): float(v) for k, v in data.get("injury_rest_by_hero", {}).items()},
            satisfaction_delta_by_hero={str(k): int(v) for k, v in data.get("satisfaction_delta_by_hero", {}).items()},
            training_points_by_hero={str(k): int(v) for k, v in data.get("training_points_by_hero", {}).items()},
            consequence_summary=list(data.get("consequence_summary", [])),
        )

@dataclass
class CampaignDecisionEvent:
    event_id: str
    task_id: str
    title: str
    description: str
    choices: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id,
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "choices": list(self.choices),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CampaignDecisionEvent":
        return cls(
            event_id=str(data["event_id"]),
            task_id=str(data["task_id"]),
            title=str(data["title"]),
            description=str(data["description"]),
            choices=list(data.get("choices", [])),
        )


@dataclass
class CampaignRuntime:
    active: bool = True
    paused: bool = False
    elapsed_time: float = 0.0
    total_spawns: int = 0
    max_spawns: int = 18
    next_spawn_time: float = 2.0
    active_tasks: List[CampaignTask] = field(default_factory=list)
    hero_states: Dict[str, HeroDispatchState] = field(default_factory=dict)
    open_decision_event: Optional[CampaignDecisionEvent] = None
    event_log: List[str] = field(default_factory=list)
    completed_task_ids: List[str] = field(default_factory=list)
    expired_task_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "active": self.active,
            "paused": self.paused,
            "elapsed_time": self.elapsed_time,
            "total_spawns": self.total_spawns,
            "max_spawns": self.max_spawns,
            "next_spawn_time": self.next_spawn_time,
            "active_tasks": [task.to_dict() for task in self.active_tasks],
            "hero_states": {
                hero_name: state.to_dict()
                for hero_name, state in self.hero_states.items()
            },
            "open_decision_event": self.open_decision_event.to_dict() if self.open_decision_event else None,
            "event_log": list(self.event_log),
            "completed_task_ids": list(self.completed_task_ids),
            "expired_task_ids": list(self.expired_task_ids),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CampaignRuntime":
        open_event = data.get("open_decision_event")
        return cls(
            active=bool(data.get("active", True)),
            paused=bool(data.get("paused", False)),
            elapsed_time=float(data.get("elapsed_time", 0.0)),
            total_spawns=int(data.get("total_spawns", 0)),
            max_spawns=int(data.get("max_spawns", 18)),
            next_spawn_time=float(data.get("next_spawn_time", 2.0)),
            active_tasks=[CampaignTask.from_dict(task) for task in data.get("active_tasks", [])],
            hero_states={
                hero_name: HeroDispatchState.from_dict(state_data)
                for hero_name, state_data in data.get("hero_states", {}).items()
            },
            open_decision_event=CampaignDecisionEvent.from_dict(open_event) if open_event else None,
            event_log=list(data.get("event_log", [])),
            completed_task_ids=list(data.get("completed_task_ids", [])),
            expired_task_ids=list(data.get("expired_task_ids", [])),
        )