"""
systems/equipment/equipment_synergies.py

Evaluates broad tag-based synergy conditions across a hero's loadout.

Design intent (GDD):
  Synergies should be explicit and understandable.  They use broad tag
  conditions rather than narrow named-item pairs.  A condition like
  "gains +1 guard when paired with any shield" is preferred over
  "gains +1 guard when paired with Iron Kite Shield specifically."

  Conditions live on the item in the `synergy_conditions` list.  Each entry:
    {
      "requires_tag": "blade",   # any co-equipped item must have this tag
      "stat": "guard",           # which dispatch stat gets the bonus
      "bonus": 1,                # integer bonus amount
      "description": "..."       # human-readable explanation
    }

  The evaluator collects all tags present in the hero's full loadout
  (excluding the item being evaluated), then checks each condition.
  Matching conditions contribute their bonus to the hero's effective stats.
"""

from __future__ import annotations

from typing import Dict, List

from models import Hero, Item


# ---------------------------------------------------------------------------
# Tag collection
# ---------------------------------------------------------------------------

def loadout_tags(hero: Hero, exclude_item: Item | None = None) -> List[str]:
    """
    Return a flat list of all tags across the hero's equipped items,
    optionally excluding one item (used when evaluating that item's own
    conditions so it doesn't trigger off itself).
    """
    tags: List[str] = []
    for item in hero.equipment.values():
        if item is exclude_item:
            continue
        tags.extend(item.tags)
    return tags


# ---------------------------------------------------------------------------
# Condition evaluation
# ---------------------------------------------------------------------------

def evaluate_synergy_condition(condition: Dict, available_tags: List[str]) -> bool:
    """Return True if this condition is satisfied by the available tag pool."""
    required = str(condition.get("requires_tag", "")).strip().lower()
    if not required:
        return False
    return required in [t.lower() for t in available_tags]


def active_synergies_for_item(item: Item, hero: Hero) -> List[Dict]:
    """
    Return all synergy conditions on `item` that are currently satisfied
    by the rest of the hero's loadout.
    """
    if not item.synergy_conditions:
        return []

    other_tags = loadout_tags(hero, exclude_item=item)
    return [
        cond for cond in item.synergy_conditions
        if evaluate_synergy_condition(cond, other_tags)
    ]


def all_active_synergies(hero: Hero) -> Dict[str, List[Dict]]:
    """
    Return a dict of { item_name: [active_condition, ...] } for every item
    in the hero's loadout that has at least one active synergy condition.
    """
    result: Dict[str, List[Dict]] = {}
    for item in hero.equipment.values():
        active = active_synergies_for_item(item, hero)
        if active:
            result[item.name] = active
    return result


# ---------------------------------------------------------------------------
# Stat bonus aggregation
# ---------------------------------------------------------------------------

def synergy_stat_bonuses(hero: Hero) -> Dict[str, int]:
    """
    Aggregate all stat bonuses from active synergy conditions across the
    hero's full loadout.  Returns a dict of stat_name → total_bonus.
    """
    bonuses: Dict[str, int] = {}
    for item in hero.equipment.values():
        for cond in active_synergies_for_item(item, hero):
            stat  = str(cond.get("stat", "")).strip()
            bonus = int(cond.get("bonus", 0))
            if stat:
                bonuses[stat] = bonuses.get(stat, 0) + bonus
    return bonuses


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def synergy_summary_lines(hero: Hero) -> List[str]:
    """
    Human-readable list of active synergy descriptions, suitable for UI
    display in the inventory or loadout panels.
    """
    lines: List[str] = []
    for item in hero.equipment.values():
        for cond in active_synergies_for_item(item, hero):
            desc = str(cond.get("description", "")).strip()
            if desc:
                lines.append(f"{item.name}: {desc}")
    return lines


def has_any_active_synergy(hero: Hero) -> bool:
    return any(
        active_synergies_for_item(item, hero)
        for item in hero.equipment.values()
    )