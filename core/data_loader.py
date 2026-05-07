import json
from pathlib import Path
from typing import Any, Dict, List

from .contract_attitudes import random_contract_attitude
from .growth_rates import random_growth_rate
from .hero_specialties import random_specialty_for_class
from models import Hero, Item


DATA_DIR = Path("data")

HEROES_PATH = DATA_DIR / "heroes.json"
ITEMS_PATH = DATA_DIR / "items.json"
EVENTS_PATH = DATA_DIR / "events.json"
HERO_NAMES_PATH = DATA_DIR / "hero_names.json"
HERO_GENERATION_RULES_PATH = DATA_DIR / "hero_generation_rules.json"


def load_json_file(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Required data file not found: {path}")

    with path.open("r", encoding="utf-8") as data_file:
        return json.load(data_file)


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


def item_from_data(data: Dict[str, Any]) -> Item:
    return Item(
        name=data["name"],
        slot=data["slot"],
        stat_bonuses=dict(data.get("stat_bonuses", {})),
        value=int(data["value"]),
        rarity=data.get("rarity", "Common"),
        damage_type_bonus=dict(data.get("damage_type_bonus", {})),
        enemy_type_bonus=dict(data.get("enemy_type_bonus", {})),
        enemy_type_resistance=dict(data.get("enemy_type_resistance", {})),
        class_restrictions=list(data.get("class_restrictions", [])),
        enemy_affinity=list(data.get("enemy_affinity", [])),
    )


def load_heroes() -> List[Hero]:
    return [hero_from_data(hero_data) for hero_data in load_json_file(HEROES_PATH)]


def load_items() -> List[Item]:
    return [item_from_data(item_data) for item_data in load_json_file(ITEMS_PATH)]


def load_events() -> List[Dict[str, Any]]:
    if not EVENTS_PATH.exists():
        return []

    raw = load_json_file(EVENTS_PATH)
    if not isinstance(raw, list):
        return []

    return [dict(event) for event in raw]


def load_hero_names() -> Dict[str, Any]:
    raw = load_json_file(HERO_NAMES_PATH)
    return dict(raw)


def load_hero_generation_rules() -> Dict[str, Any]:
    raw = load_json_file(HERO_GENERATION_RULES_PATH)
    return dict(raw)