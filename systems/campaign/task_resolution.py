from __future__ import annotations

from typing import Any, Dict, List

from systems.campaign.task_scoring import (
    DISPATCH_STATS,
    calculate_task_success_chance,
    combined_party_dispatch_stats,
    evaluate_stat_rule,
    format_dispatch_stats,
    format_stat_rule_short,
    get_task_stat_rules,
    hero_dispatch_stats,
    normalize_rule,
    resolve_task_outcome_from_chance,
)


def build_task_resolution_summary(task, heroes: List[Any], roll_value: float) -> Dict[str, Any]:
    """
    High-level task result payload used by campaign systems and UI.

    This is intentionally a thin orchestration layer right now.
    Later it is the right place to apply:
    - decision branch modifiers
    - follow-up task unlocks
    - linked task consequences
    - task-specific reward overrides
    """
    outcome = resolve_task_outcome_from_chance(task, heroes, roll_value)

    return {
        "task_id": getattr(task, "task_id", ""),
        "task_type": getattr(task, "task_type", "Unknown Task"),
        "heroes": list(heroes),
        "provided_stats": dict(outcome["provided_stats"]),
        "stat_rules": dict(outcome["stat_rules"]),
        "stat_breakdown": dict(outcome["stat_breakdown"]),
        "fit_score": float(outcome["fit_score"]),
        "success_chance": float(outcome["success_chance"]),
        "roll_value": float(outcome["roll_value"]),
        "outcome_band": str(outcome["outcome_band"]),
        "payout_multiplier": float(outcome["payout_multiplier"]),
        "xp_multiplier": float(outcome["xp_multiplier"]),
        "injury_profile": dict(outcome["injury_profile"]),
        "satisfaction_delta": int(outcome["satisfaction_delta"]),
        "ability_modifiers": dict(outcome.get("ability_modifiers", {})),
        "branch_flags": {},
        "linked_tasks": [],
        "reward_modifiers": {},
    }


def apply_resolution_branch_modifiers(
    resolution_data: Dict[str, Any],
    branch_flags: Dict[str, Any] | None = None,
    linked_tasks: List[Dict[str, Any]] | None = None,
    reward_modifiers: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Extend a resolution payload with future decision/branch data.

    Keeping this separate now makes it easy to later inject:
    - question/answer outcomes
    - mission interruption consequences
    - linked task chains
    """
    updated = dict(resolution_data)
    updated["branch_flags"] = dict(branch_flags or {})
    updated["linked_tasks"] = list(linked_tasks or [])
    updated["reward_modifiers"] = dict(reward_modifiers or {})
    return updated


def review_data_for_task(task, heroes: List[Any]) -> Dict[str, Any]:
    """
    Build UI-friendly review data without rolling the task outcome.
    Useful for post-task review panels or debugging.
    """
    chance_data = calculate_task_success_chance(task, heroes)

    return {
        "task_id": getattr(task, "task_id", ""),
        "task_type": getattr(task, "task_type", "Unknown Task"),
        "provided_stats": dict(chance_data["provided_stats"]),
        "stat_rules": dict(chance_data["stat_rules"]),
        "stat_breakdown": dict(chance_data["stat_breakdown"]),
        "fit_score": float(chance_data["fit_score"]),
        "success_chance": float(chance_data["success_chance"]),
        "ability_modifiers": dict(chance_data.get("ability_modifiers", {})),
    }


__all__ = [
    "DISPATCH_STATS",
    "hero_dispatch_stats",
    "combined_party_dispatch_stats",
    "normalize_rule",
    "get_task_stat_rules",
    "evaluate_stat_rule",
    "format_stat_rule_short",
    "format_dispatch_stats",
    "calculate_task_success_chance",
    "resolve_task_outcome_from_chance",
    "build_task_resolution_summary",
    "apply_resolution_branch_modifiers",
    "review_data_for_task",
]