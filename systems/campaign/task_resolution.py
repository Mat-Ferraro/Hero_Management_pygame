from __future__ import annotations

from typing import Dict, List

DISPATCH_STATS = ["might", "guard", "wit", "presence", "swift"]


def safe_total_stat(hero, stat_name: str) -> int:
    try:
        value = hero.total_stat(stat_name)
        return max(0, int(value))
    except Exception:
        return max(0, int(getattr(hero, "stats", {}).get(stat_name, 0)))


def hero_dispatch_stats(hero) -> Dict[str, int]:
    hero_class = getattr(hero, "hero_class", "")
    subclass = (getattr(hero, "subclass", None) or "").lower()

    stats = {
        "might": safe_total_stat(hero, "might"),
        "guard": max(0, int(round((safe_total_stat(hero, "might") + safe_total_stat(hero, "spirit")) / 2))),
        "wit": safe_total_stat(hero, "mind"),
        "presence": safe_total_stat(hero, "spirit"),
        "swift": safe_total_stat(hero, "agility"),
    }

    if hero_class == "Warrior":
        stats["might"] += 1
        stats["guard"] += 1
    elif hero_class == "Rogue":
        stats["swift"] += 1
        stats["wit"] += 1
    elif hero_class == "Cleric":
        stats["guard"] += 1
        stats["presence"] += 1
    elif hero_class == "Mage":
        stats["wit"] += 2

    # Light placeholder hooks for future subclass identity.
    if "vanguard" in subclass:
        stats["might"] += 1
        stats["swift"] += 1
    elif "warden" in subclass:
        stats["guard"] += 2
    elif "captain" in subclass:
        stats["presence"] += 1
        stats["guard"] += 1
    elif "scout" in subclass:
        stats["swift"] += 2
    elif "fixer" in subclass:
        stats["presence"] += 1
        stats["wit"] += 1
    elif "oracle" in subclass:
        stats["wit"] += 1
        stats["presence"] += 1
    elif "templar" in subclass:
        stats["guard"] += 1
        stats["might"] += 1
    elif "arcanist" in subclass:
        stats["wit"] += 2
    elif "seer" in subclass:
        stats["wit"] += 1
        stats["swift"] += 1
    elif "spellblade" in subclass:
        stats["might"] += 1
        stats["wit"] += 1

    return stats


def combined_party_dispatch_stats(heroes: List) -> Dict[str, int]:
    totals = {stat: 0 for stat in DISPATCH_STATS}

    for hero in heroes:
        hero_stats = hero_dispatch_stats(hero)
        for stat in DISPATCH_STATS:
            totals[stat] += int(hero_stats.get(stat, 0))

    return totals


def stat_coverage(required: Dict[str, int], provided: Dict[str, int]) -> Dict[str, float]:
    coverage = {}
    for stat in DISPATCH_STATS:
        needed = max(0, int(required.get(stat, 0)))
        if needed <= 0:
            coverage[stat] = 1.0
            continue
        have = max(0, int(provided.get(stat, 0)))
        coverage[stat] = min(1.0, have / needed)
    return coverage


def overall_coverage_ratio(required: Dict[str, int], provided: Dict[str, int]) -> float:
    relevant_stats = [stat for stat in DISPATCH_STATS if int(required.get(stat, 0)) > 0]
    if not relevant_stats:
        return 1.0

    coverage = stat_coverage(required, provided)
    return sum(coverage[stat] for stat in relevant_stats) / len(relevant_stats)


def preferred_class_bonus(task, heroes: List) -> float:
    preferred = set(getattr(task, "preferred_classes", []))
    if not preferred:
        return 0.0

    matches = 0
    for hero in heroes:
        if getattr(hero, "hero_class", None) in preferred:
            matches += 1

    if matches <= 0:
        return 0.0

    return min(0.15, matches * 0.05)


def party_size_bonus(task, heroes: List) -> float:
    max_heroes = max(1, int(getattr(task, "max_heroes", 1)))
    if not heroes:
        return 0.0

    fill_ratio = min(1.0, len(heroes) / max_heroes)
    return fill_ratio * 0.05


def calculate_task_success(task, heroes: List) -> Dict:
    provided = combined_party_dispatch_stats(heroes)
    coverage_ratio = overall_coverage_ratio(task.required_stats, provided)

    success_chance = coverage_ratio
    success_chance += preferred_class_bonus(task, heroes)
    success_chance += party_size_bonus(task, heroes)
    success_chance = max(0.0, min(1.0, success_chance))

    if success_chance >= 0.90:
        outcome_band = "great_success"
        payout_multiplier = 1.25
        xp_multiplier = 1.20
    elif success_chance >= 0.75:
        outcome_band = "success"
        payout_multiplier = 1.00
        xp_multiplier = 1.00
    elif success_chance >= 0.50:
        outcome_band = "partial_success"
        payout_multiplier = 0.65
        xp_multiplier = 0.75
    else:
        outcome_band = "failure"
        payout_multiplier = 0.0
        xp_multiplier = 0.35

    return {
        "required_stats": dict(task.required_stats),
        "provided_stats": provided,
        "coverage_ratio": success_chance,
        "raw_coverage_ratio": coverage_ratio,
        "success_chance": success_chance,
        "outcome_band": outcome_band,
        "payout_multiplier": payout_multiplier,
        "xp_multiplier": xp_multiplier,
    }


def format_dispatch_stats(stats: Dict[str, int]) -> str:
    return (
        f"M {stats.get('might', 0)} | "
        f"G {stats.get('guard', 0)} | "
        f"W {stats.get('wit', 0)} | "
        f"P {stats.get('presence', 0)} | "
        f"S {stats.get('swift', 0)}"
    )