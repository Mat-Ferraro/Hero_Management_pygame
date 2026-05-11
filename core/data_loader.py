"""
core/data_loader.py

Loads hand-authored JSON data files and converts them into model instances.

Item loading (v2 schema):
  Items now use `category` (Weapon / Armor / Utility / Trinket) instead of
  the old free-string `slot`.  Old saves and any JSON that still has `slot`
  are migrated automatically.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from .contract_attitudes import random_contract_attitude
from .growth_rates import random_growth_rate
from .hero_specialties import random_specialty_for_class
from models import Hero, Item


DATA_DIR = Path("data")

HEROES_PATH               = DATA_DIR / "heroes.json"
ITEMS_PATH                = DATA_DIR / "items.json"
EVENTS_PATH               = DATA_DIR / "events.json"
HERO_NAMES_PATH           = DATA_DIR / "hero_names.json"
HERO_GENERATION_RULES_PATH = DATA_DIR / "hero_generation_rules.json"


# ---------------------------------------------------------------------------
# Slot → Category migration map (old schema had free-string slots)
# ---------------------------------------------------------------------------

_SLOT_TO_CATEGORY: Dict[str, str] = {
    "weapon":  "Weapon",
    "armor":   "Armor",
    "armour":  "Armor",
    "utility": "Utility",
    "trinket": "Trinket",
    "boots":   "Utility",
    "cloak":   "Armor",
    "ring":    "Trinket",
    "amulet":  "Trinket",
    "offhand": "Armor",
}


def _resolve_category(data: Dict[str, Any]) -> str:
    """Derive canonical category from new `category` key or old `slot` key."""
    if "category" in data:
        raw = str(data["category"]).strip().capitalize()
        if raw in ("Weapon", "Armor", "Utility", "Trinket"):
            return raw
        return _SLOT_TO_CATEGORY.get(raw.lower(), "Utility")

    if "slot" in data:
        return _SLOT_TO_CATEGORY.get(str(data["slot"]).lower(), "Utility")

    return "Utility"


# ---------------------------------------------------------------------------
# JSON loading
# ---------------------------------------------------------------------------

def load_json_file(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Required data file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

def hero_from_data(data: Dict[str, Any]) -> Hero:
    hero_class = str(data["hero_class"])
    return Hero(
        name=data["name"],
        hero_class=hero_class,
        age=int(data["age"]),
        level=int(data.get("level", 1)),
        xp=int(data.get("xp", 0)),
        stats=dict(data["stats"]),
        signing_bonus=int(data["signing_bonus"]),
        wage_per_year=int(data["wage_per_year"]),
        contract_years=int(data["contract_years"]),
        specialty=data.get("specialty") or random_specialty_for_class(hero_class),
        growth_rate=data.get("growth_rate") or random_growth_rate(),
        contract_attitude=data.get("contract_attitude") or random_contract_attitude(),
    )


# ---------------------------------------------------------------------------
# Item
# ---------------------------------------------------------------------------

def item_from_data(data: Dict[str, Any]) -> Item:
    """Build an Item from JSON.  Handles both new (category) and old (slot) schema."""
    return Item(
        name=str(data["name"]),
        category=_resolve_category(data),
        rarity=data.get("rarity", "Common"),
        lore=data.get("lore", ""),
        value=int(data.get("value", 0)),
        stat_bonuses=dict(data.get("stat_bonuses", {})),
        damage_type_bonus=dict(data.get("damage_type_bonus", {})),
        enemy_type_bonus=dict(data.get("enemy_type_bonus", {})),
        enemy_type_resistance=dict(data.get("enemy_type_resistance", {})),
        tags=list(data.get("tags", [])),
        drawbacks=list(data.get("drawbacks", [])),
        synergy_conditions=list(data.get("synergy_conditions", [])),
        class_restrictions=list(data.get("class_restrictions", [])),
        enemy_affinity=list(data.get("enemy_affinity", [])),
        consumable=bool(data.get("consumable", False)),
        equip_capacity_cost=int(data.get("equip_capacity_cost", 1)),
        upgrade_from=data.get("upgrade_from"),
        upgrade_paths=list(data.get("upgrade_paths", [])),
        story_flags=list(data.get("story_flags", [])),
    )


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_heroes() -> List[Hero]:
    return [hero_from_data(d) for d in load_json_file(HEROES_PATH)]


def load_items() -> List[Item]:
    return [item_from_data(d) for d in load_json_file(ITEMS_PATH)]


def load_events() -> List[Dict[str, Any]]:
    if not EVENTS_PATH.exists():
        return []
    raw = load_json_file(EVENTS_PATH)
    if not isinstance(raw, list):
        return []
    return [dict(e) for e in raw]


def load_hero_names() -> Dict[str, Any]:
    return dict(load_json_file(HERO_NAMES_PATH))


def load_hero_generation_rules() -> Dict[str, Any]:
    return dict(load_json_file(HERO_GENERATION_RULES_PATH))