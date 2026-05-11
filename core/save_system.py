"""
core/save_system.py

Serialisation and deserialisation for all game state.

Version history
---------------
10  — previous format (9-axis ManagerReputation: overall, reliability,
       safety, development, protector, warrior, rogue, cleric, mage)
11  — reputation collapsed to single-axis RecentReputation (standing int
       + history list).  Old saves load gracefully: if the "standing" key
       is absent but old multi-axis keys are present, standing is derived
       by clamping the old "overall" score to [-2, +2] so the save is
       still usable.
"""

import json
from pathlib import Path
from typing import Any, Dict

from .game_state import BereavementPayment, GameState
from .manager_reputation import RecentReputation
from models import Hero, Item
from systems.campaign.campaign_models import CampaignRuntime
from systems.guild.guild_upgrades import guild_upgrades_from_dict, guild_upgrades_to_dict
from systems.guild.rival_guilds import ensure_rival_guild_state


SAVE_DIR = Path("saves")
DEFAULT_SAVE_PATH = SAVE_DIR / "save_slot_1.json"
SAVE_VERSION = 11


# ---------------------------------------------------------------------------
# Item
# ---------------------------------------------------------------------------

def item_to_dict(item: Item) -> Dict[str, Any]:
    return {
        "name": item.name,
        "category": item.category,
        "rarity": item.rarity,
        "lore": item.lore,
        "value": int(item.value),
        "stat_bonuses": dict(item.stat_bonuses),
        "damage_type_bonus": dict(item.damage_type_bonus),
        "enemy_type_bonus": dict(item.enemy_type_bonus),
        "enemy_type_resistance": dict(item.enemy_type_resistance),
        "tags": list(item.tags),
        "drawbacks": list(item.drawbacks),
        "synergy_conditions": list(item.synergy_conditions),
        "class_restrictions": list(item.class_restrictions),
        "enemy_affinity": list(item.enemy_affinity),
        "consumable": bool(item.consumable),
        "equip_capacity_cost": int(item.equip_capacity_cost),
        "upgrade_from": item.upgrade_from,
        "upgrade_paths": list(item.upgrade_paths),
        "story_flags": list(item.story_flags),
    }


def item_from_dict(data: Dict[str, Any]) -> Item:
    """
    Reconstruct an Item from saved data.
    Handles both new schema (category) and old schema (slot) for
    backward-compatibility with pre-v11 save files.
    """
    from core.data_loader import _resolve_category
    category = _resolve_category(data)

    return Item(
        name=str(data["name"]),
        category=category,
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
# Hero
# ---------------------------------------------------------------------------

def hero_to_dict(hero: Hero) -> Dict[str, Any]:
    from systems.progression.hero_progression import ensure_progression_fields, progression_to_dict

    ensure_progression_fields(hero)

    return {
        "name": hero.name,
        "hero_class": hero.hero_class,
        "age": int(hero.age),
        "level": int(hero.level),
        "xp": int(hero.xp),
        "stats": dict(hero.stats),
        "signing_bonus": int(hero.signing_bonus),
        "wage_per_year": int(hero.wage_per_year),
        "contract_years": int(hero.contract_years),
        "specialty": hero.specialty,
        "growth_rate": hero.growth_rate,
        "contract_attitude": hero.contract_attitude,
        "equipment": {
            slot: item_to_dict(item)
            for slot, item in hero.equipment.items()
        },
        "injured_years_remaining": int(hero.injured_years_remaining),
        "wound_history": list(hero.wound_history),
        "current_health": hero.current_health,
        "debt": int(hero.debt),
        "is_temporary_survivor": bool(hero.is_temporary_survivor),
        "satisfaction": int(getattr(hero, "satisfaction", 80)),
        "participated_this_cycle": bool(getattr(hero, "participated_this_cycle", False)),
        "subclass": getattr(hero, "subclass", None),
        "special_ability": getattr(hero, "special_ability", None),
        "training_points": int(getattr(hero, "training_points", 0)),
        "training_path_progress": dict(getattr(hero, "training_path_progress", {})),
        "unlocked_subclasses": list(getattr(hero, "unlocked_subclasses", [])),
        "unlocked_abilities": list(getattr(hero, "unlocked_abilities", [])),
        "primary_subclass": getattr(hero, "primary_subclass", None),
        "progression": progression_to_dict(hero),
    }


def hero_from_dict(data: Dict[str, Any]) -> Hero:
    from systems.progression.hero_progression import apply_progression_from_dict, ensure_progression_fields

    hero = Hero(
        name=data["name"],
        hero_class=data["hero_class"],
        age=int(data["age"]),
        level=int(data["level"]),
        xp=int(data["xp"]),
        stats=dict(data["stats"]),
        signing_bonus=int(data["signing_bonus"]),
        wage_per_year=int(data["wage_per_year"]),
        contract_years=int(data["contract_years"]),
        specialty=data.get("specialty", "Adventurer"),
        growth_rate=data.get("growth_rate", "Talented"),
        contract_attitude=data.get("contract_attitude", "Pragmatic"),
        equipment={
            slot: item_from_dict(item_data)
            for slot, item_data in data.get("equipment", {}).items()
        },
        injured_years_remaining=int(data.get("injured_years_remaining", 0)),
        wound_history=list(data.get("wound_history", [])),
        current_health=data.get("current_health"),
        debt=int(data.get("debt", 0)),
        is_temporary_survivor=bool(data.get("is_temporary_survivor", False)),
        satisfaction=int(data.get("satisfaction", 80)),
        participated_this_cycle=bool(data.get("participated_this_cycle", False)),
        subclass=data.get("subclass"),
        special_ability=data.get("special_ability"),
        training_points=int(data.get("training_points", 0)),
        training_path_progress=dict(data.get("training_path_progress", {})),
        unlocked_subclasses=list(data.get("unlocked_subclasses", [])),
        unlocked_abilities=list(data.get("unlocked_abilities", [])),
        primary_subclass=data.get("primary_subclass"),
    )

    ensure_progression_fields(hero)
    apply_progression_from_dict(hero, data.get("progression"))
    return hero


# ---------------------------------------------------------------------------
# Reputation  (v11: single-axis RecentReputation)
# ---------------------------------------------------------------------------

def reputation_to_dict(reputation: RecentReputation) -> Dict[str, Any]:
    return {
        "standing": int(reputation.standing),
        "history": list(reputation.history),
    }


def reputation_from_dict(data: Dict[str, Any]) -> RecentReputation:
    """
    Loads a RecentReputation from saved data.

    Backward-compatible with v10 saves: if "standing" is absent but the
    old "overall" key is present, we derive a standing value by clamping
    the old score to [-2, +2] so that existing saves load cleanly.
    """
    if "standing" in data:
        standing = int(data["standing"])
    elif "overall" in data:
        # Migrate from v10: scale old overall [-100, +100] → [-2, +2]
        old_overall = int(data.get("overall", 0))
        standing = max(-2, min(2, old_overall // 35))
    else:
        standing = 0

    return RecentReputation(
        standing=standing,
        history=list(data.get("history", [])),
    )


# ---------------------------------------------------------------------------
# BereavementPayment
# ---------------------------------------------------------------------------

def bereavement_to_dict(payment: BereavementPayment) -> Dict[str, Any]:
    return {
        "hero_name": payment.hero_name,
        "amount": int(payment.amount),
    }


def bereavement_from_dict(data: Dict[str, Any]) -> BereavementPayment:
    return BereavementPayment(
        hero_name=data["hero_name"],
        amount=int(data["amount"]),
    )


# ---------------------------------------------------------------------------
# Rival guild
# ---------------------------------------------------------------------------

def rival_guild_to_dict(guild: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": guild.get("name", "Unknown Rival"),
        "style": guild.get("style", "Unknown"),
        "wealth_bias": int(guild.get("wealth_bias", 0)),
        "aggression": int(guild.get("aggression", 0)),
        "prestige": int(guild.get("prestige", 0)),
        "rookie_interest": int(guild.get("rookie_interest", 0)),
        "class_preference": guild.get("class_preference"),
        "tagline": guild.get("tagline", ""),
        "roster": [hero_to_dict(hero) for hero in guild.get("roster", [])],
        "total_signings": int(guild.get("total_signings", 0)),
        "recent_pickups": list(guild.get("recent_pickups", [])),
    }


def rival_guild_from_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": data.get("name", "Unknown Rival"),
        "style": data.get("style", "Unknown"),
        "wealth_bias": int(data.get("wealth_bias", 0)),
        "aggression": int(data.get("aggression", 0)),
        "prestige": int(data.get("prestige", 0)),
        "rookie_interest": int(data.get("rookie_interest", 0)),
        "class_preference": data.get("class_preference"),
        "tagline": data.get("tagline", ""),
        "roster": [hero_from_dict(hero_data) for hero_data in data.get("roster", [])],
        "total_signings": int(data.get("total_signings", 0)),
        "recent_pickups": list(data.get("recent_pickups", [])),
    }


# ---------------------------------------------------------------------------
# Contract offer
# ---------------------------------------------------------------------------

def contract_offer_to_dict(offer: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "hero_name": offer.get("hero_name", ""),
        "offered_campaigns": int(offer.get("offered_campaigns", 1)),
        "offered_signing_fee": int(offer.get("offered_signing_fee", 25)),
    }


def contract_offer_from_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "hero_name": data.get("hero_name", ""),
        "offered_campaigns": int(data.get("offered_campaigns", 1)),
        "offered_signing_fee": int(data.get("offered_signing_fee", 25)),
    }


# ---------------------------------------------------------------------------
# Campaign runtime
# ---------------------------------------------------------------------------

def campaign_runtime_to_dict(runtime: CampaignRuntime | None) -> Dict[str, Any] | None:
    if runtime is None:
        return None
    return runtime.to_dict()


def campaign_runtime_from_dict(data: Dict[str, Any] | None) -> CampaignRuntime | None:
    if not data:
        return None
    return CampaignRuntime.from_dict(data)


# ---------------------------------------------------------------------------
# Full game state
# ---------------------------------------------------------------------------

def game_state_to_dict(state: GameState) -> Dict[str, Any]:
    ensure_rival_guild_state(state)

    return {
        "version": SAVE_VERSION,
        "expedition": int(state.expedition),
        "year": int(state.year),
        "gold": int(state.gold),
        "roster": [hero_to_dict(hero) for hero in state.roster],
        "available_contracts": [hero_to_dict(hero) for hero in state.available_contracts],
        "inventory": [item_to_dict(item) for item in state.inventory],
        "retired_heroes": [hero_to_dict(hero) for hero in state.retired_heroes],
        "fallen_heroes": [hero_to_dict(hero) for hero in state.fallen_heroes],
        "reputation": reputation_to_dict(state.reputation),
        "pending_bereavement_payments": [
            bereavement_to_dict(payment)
            for payment in state.pending_bereavement_payments
        ],
        "guild_upgrades": guild_upgrades_to_dict(state.guild_upgrades),
        "rival_guilds": [rival_guild_to_dict(guild) for guild in state.rival_guilds],
        "contract_offers": [contract_offer_to_dict(offer) for offer in state.contract_offers],
        "renewal_offers": [contract_offer_to_dict(offer) for offer in state.renewal_offers],
        "contract_round": int(state.contract_round),
        "market_history": list(state.market_history),
        "seasonal_contract_pool": [
            hero_to_dict(hero)
            for hero in getattr(state, "seasonal_contract_pool", [])
        ],
        "market_stage": int(getattr(state, "market_stage", 1)),
        "market_stage_max": int(getattr(state, "market_stage_max", 3)),
        "market_cycle": int(getattr(state, "market_cycle", 1)),
        "market_fallback_open": bool(getattr(state, "market_fallback_open", False)),
        "market_closed": bool(getattr(state, "market_closed", False)),
        "campaign_runtime": campaign_runtime_to_dict(getattr(state, "campaign_runtime", None)),
    }


def game_state_from_dict(data: Dict[str, Any]) -> GameState:
    _version = int(data.get("version", 0))

    state = GameState(
        expedition=int(data.get("expedition", 1)),
        year=int(data.get("year", 1)),
        gold=int(data.get("gold", 0)),
        roster=[hero_from_dict(hero_data) for hero_data in data.get("roster", [])],
        available_contracts=[
            hero_from_dict(hero_data)
            for hero_data in data.get("available_contracts", [])
        ],
        inventory=[item_from_dict(item_data) for item_data in data.get("inventory", [])],
        retired_heroes=[hero_from_dict(hero_data) for hero_data in data.get("retired_heroes", [])],
        fallen_heroes=[hero_from_dict(hero_data) for hero_data in data.get("fallen_heroes", [])],
        reputation=reputation_from_dict(data.get("reputation", {})),
        pending_bereavement_payments=[
            bereavement_from_dict(payment_data)
            for payment_data in data.get("pending_bereavement_payments", [])
        ],
        guild_upgrades=guild_upgrades_from_dict(data.get("guild_upgrades", {})),
        rival_guilds=[rival_guild_from_dict(guild_data) for guild_data in data.get("rival_guilds", [])],
        contract_offers=[
            contract_offer_from_dict(offer_data)
            for offer_data in data.get("contract_offers", [])
        ],
        renewal_offers=[
            contract_offer_from_dict(offer_data)
            for offer_data in data.get("renewal_offers", [])
        ],
        contract_round=int(data.get("contract_round", 1)),
        market_history=list(data.get("market_history", [])),
        seasonal_contract_pool=[
            hero_from_dict(hero_data)
            for hero_data in data.get("seasonal_contract_pool", [])
        ],
        market_stage=int(data.get("market_stage", 1)),
        market_stage_max=int(data.get("market_stage_max", 3)),
        market_cycle=int(data.get("market_cycle", 1)),
        market_fallback_open=bool(data.get("market_fallback_open", False)),
        market_closed=bool(data.get("market_closed", False)),
        campaign_runtime=campaign_runtime_from_dict(data.get("campaign_runtime")),
    )

    ensure_rival_guild_state(state)

    if not getattr(state, "seasonal_contract_pool", []):
        state.seasonal_contract_pool = list(state.available_contracts)

    return state


def save_game(state: GameState, path: Path = DEFAULT_SAVE_PATH) -> Path:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    data = game_state_to_dict(state)

    with path.open("w", encoding="utf-8") as save_file:
        json.dump(data, save_file, indent=2)

    return path


def load_game(path: Path = DEFAULT_SAVE_PATH) -> GameState:
    if not path.exists():
        raise FileNotFoundError(f"No save file found at {path}")

    with path.open("r", encoding="utf-8") as save_file:
        data = json.load(save_file)

    return game_state_from_dict(data)


def save_exists(path: Path = DEFAULT_SAVE_PATH) -> bool:
    return path.exists()