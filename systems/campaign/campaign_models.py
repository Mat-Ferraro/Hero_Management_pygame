from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def _int_tuple_or_none(value) -> Optional[Tuple[int, int]]:
    if not value:
        return None

    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return int(value[0]), int(value[1])

    return None


def _float_or_none(value) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def _choice_to_dict(choice: Any) -> Dict[str, Any]:
    if isinstance(choice, CampaignDecisionChoice):
        return choice.to_dict()

    if isinstance(choice, dict):
        return CampaignDecisionChoice.from_dict(choice).to_dict()

    return CampaignDecisionChoice(
        id="choice",
        label=str(choice),
    ).to_dict()


def _choice_from_any(value: Any) -> "CampaignDecisionChoice":
    if isinstance(value, CampaignDecisionChoice):
        return value

    if isinstance(value, dict):
        return CampaignDecisionChoice.from_dict(value)

    return CampaignDecisionChoice(
        id="choice",
        label=str(value),
    )


@dataclass
class HeroDispatchState:
    hero_name: str
    state: str = "available"
    assigned_task_id: Optional[str] = None
    current_task_id: Optional[str] = None
    travel_end_time: Optional[float] = None
    task_end_time: Optional[float] = None
    return_end_time: Optional[float] = None
    rest_end_time: Optional[float] = None
    current_position: Optional[Tuple[int, int]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hero_name": self.hero_name,
            "state": self.state,
            "assigned_task_id": self.assigned_task_id,
            "current_task_id": self.current_task_id,
            "travel_end_time": self.travel_end_time,
            "task_end_time": self.task_end_time,
            "return_end_time": self.return_end_time,
            "rest_end_time": self.rest_end_time,
            "current_position": list(self.current_position) if self.current_position else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HeroDispatchState":
        return cls(
            hero_name=str(data.get("hero_name", "")),
            state=str(data.get("state", "available")),
            assigned_task_id=data.get("assigned_task_id"),
            current_task_id=data.get("current_task_id") or data.get("assigned_task_id"),
            travel_end_time=_float_or_none(data.get("travel_end_time")),
            task_end_time=_float_or_none(data.get("task_end_time")),
            return_end_time=_float_or_none(data.get("return_end_time")),
            rest_end_time=_float_or_none(data.get("rest_end_time")),
            current_position=_int_tuple_or_none(data.get("current_position")),
        )


@dataclass
class CampaignDecisionChoice:
    id: str
    label: str
    description: str = ""
    branch_flags: Dict[str, Any] = field(default_factory=dict)
    linked_tasks: List[Dict[str, Any]] = field(default_factory=list)
    reward_modifiers: Dict[str, Any] = field(default_factory=dict)
    next_event_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "branch_flags": dict(self.branch_flags),
            "linked_tasks": list(self.linked_tasks),
            "reward_modifiers": dict(self.reward_modifiers),
            "next_event_id": self.next_event_id,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignDecisionChoice":
        return cls(
            id=str(data.get("id", "")),
            label=str(data.get("label", "Choice")),
            description=str(data.get("description", "")),
            branch_flags=dict(data.get("branch_flags", {}) or {}),
            linked_tasks=list(data.get("linked_tasks", []) or []),
            reward_modifiers=dict(data.get("reward_modifiers", {}) or {}),
            next_event_id=data.get("next_event_id"),
            tags=list(data.get("tags", []) or []),
        )


@dataclass
class CampaignDecisionEvent:
    task_id: str
    title: str
    description: str
    choices: List[CampaignDecisionChoice] = field(default_factory=list)
    event_id: Optional[str] = None
    step_index: int = 0
    total_steps: int = 1
    source: str = "task"
    branch_flags: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "choices": [_choice_to_dict(choice) for choice in self.choices],
            "event_id": self.event_id,
            "step_index": self.step_index,
            "total_steps": self.total_steps,
            "source": self.source,
            "branch_flags": dict(self.branch_flags),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignDecisionEvent":
        raw_choices = list(data.get("choices", []) or [])
        choices = [_choice_from_any(raw_choice) for raw_choice in raw_choices]

        return cls(
            task_id=str(data.get("task_id", "")),
            title=str(data.get("title", "Decision")),
            description=str(data.get("description", "")),
            choices=choices,
            event_id=data.get("event_id"),
            step_index=int(data.get("step_index", 0)),
            total_steps=max(1, int(data.get("total_steps", 1))),
            source=str(data.get("source", "task")),
            branch_flags=dict(data.get("branch_flags", {}) or {}),
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
    stat_rules: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    max_heroes: int = 1
    preferred_classes: List[str] = field(default_factory=list)
    assigned_heroes: List[str] = field(default_factory=list)

    difficulty: int = 1
    reward_gold_min: int = 0
    reward_gold_max: int = 0
    reward_xp: int = 0
    rest_duration: float = 14.0

    can_trigger_decision: bool = False
    decision_chance: float = 0.0
    decision_title: str = ""
    decision_description: str = ""
    decision_choices: List[Dict[str, Any]] = field(default_factory=list)

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

    branch_flags: Dict[str, Any] = field(default_factory=dict)
    linked_tasks: List[Dict[str, Any]] = field(default_factory=list)
    reward_modifiers: Dict[str, Any] = field(default_factory=dict)
    task_tags: List[str] = field(default_factory=list)
    origin_task_id: Optional[str] = None
    chain_id: Optional[str] = None

    def is_terminal(self) -> bool:
        return self.state in {"completed", "failed", "expired"}

    def to_dict(self) -> Dict[str, Any]:
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
            "rest_duration": self.rest_duration,
            "can_trigger_decision": self.can_trigger_decision,
            "decision_chance": self.decision_chance,
            "decision_title": self.decision_title,
            "decision_description": self.decision_description,
            "decision_choices": [dict(choice) for choice in self.decision_choices],
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
            "branch_flags": dict(self.branch_flags),
            "linked_tasks": list(self.linked_tasks),
            "reward_modifiers": dict(self.reward_modifiers),
            "task_tags": list(self.task_tags),
            "origin_task_id": self.origin_task_id,
            "chain_id": self.chain_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignTask":
        return cls(
            task_id=str(data.get("task_id", "")),
            task_type=str(data.get("task_type", "Unknown Task")),
            state=str(data.get("state", "pending")),
            map_position=_int_tuple_or_none(data.get("map_position")) or (0, 0),
            spawn_time=float(data.get("spawn_time", 0.0)),
            expire_time=float(data.get("expire_time", 0.0)),
            travel_time=float(data.get("travel_time", 0.0)),
            task_duration=float(data.get("task_duration", 0.0)),
            recommended_power=int(data.get("recommended_power", 0)),
            required_stats=dict(data.get("required_stats", {}) or {}),
            stat_rules=dict(data.get("stat_rules", {}) or {}),
            max_heroes=max(1, int(data.get("max_heroes", 1))),
            preferred_classes=list(data.get("preferred_classes", []) or []),
            assigned_heroes=list(data.get("assigned_heroes", []) or []),
            difficulty=int(data.get("difficulty", 1)),
            reward_gold_min=int(data.get("reward_gold_min", 0)),
            reward_gold_max=int(data.get("reward_gold_max", 0)),
            reward_xp=int(data.get("reward_xp", 0)),
            rest_duration=float(data.get("rest_duration", 14.0)),
            can_trigger_decision=bool(data.get("can_trigger_decision", False)),
            decision_chance=float(data.get("decision_chance", 0.0)),
            decision_title=str(data.get("decision_title", "")),
            decision_description=str(data.get("decision_description", "")),
            decision_choices=[dict(choice) for choice in list(data.get("decision_choices", []) or [])],
            started_at=_float_or_none(data.get("started_at")),
            active_until=_float_or_none(data.get("active_until")),
            completed_at=_float_or_none(data.get("completed_at")),
            acknowledged_at=_float_or_none(data.get("acknowledged_at")),
            failed_reason=str(data.get("failed_reason", "")),
            outcome_band=str(data.get("outcome_band", "")),
            success_chance=float(data.get("success_chance", 0.0)),
            coverage_ratio=float(data.get("coverage_ratio", 0.0)),
            payout_multiplier=float(data.get("payout_multiplier", 1.0)),
            xp_multiplier=float(data.get("xp_multiplier", 1.0)),
            outcome_summary=str(data.get("outcome_summary", "")),
            injured_heroes=list(data.get("injured_heroes", []) or []),
            injury_rest_by_hero={
                str(hero_name): float(rest_value)
                for hero_name, rest_value in dict(data.get("injury_rest_by_hero", {}) or {}).items()
            },
            satisfaction_delta_by_hero={
                str(hero_name): int(delta)
                for hero_name, delta in dict(data.get("satisfaction_delta_by_hero", {}) or {}).items()
            },
            training_points_by_hero={
                str(hero_name): int(points)
                for hero_name, points in dict(data.get("training_points_by_hero", {}) or {}).items()
            },
            consequence_summary=list(data.get("consequence_summary", []) or []),
            branch_flags=dict(data.get("branch_flags", {}) or {}),
            linked_tasks=list(data.get("linked_tasks", []) or []),
            reward_modifiers=dict(data.get("reward_modifiers", {}) or {}),
            task_tags=list(data.get("task_tags", []) or []),
            origin_task_id=data.get("origin_task_id"),
            chain_id=data.get("chain_id"),
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

    def to_dict(self) -> Dict[str, Any]:
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
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignRuntime":
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
                for hero_name, state_data in dict(data.get("hero_states", {}) or {}).items()
            },
            open_decision_event=CampaignDecisionEvent.from_dict(open_event) if open_event else None,
            event_log=list(data.get("event_log", []) or []),
            completed_task_ids=list(data.get("completed_task_ids", []) or []),
            expired_task_ids=list(data.get("expired_task_ids", []) or []),
        )