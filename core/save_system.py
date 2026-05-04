import json
from pathlib import Path
from typing import Dict

from game_state import BereavementPayment, GameState
from manager_reputation import ManagerReputation
from models import Dungeon, Hero, Item
from systems.campaign.campaign_models import CampaignRuntime
from systems.guild_upgrades import guild_upgrades_from_dict, guild_upgrades_to_dict
from systems.rival_guilds import ensure_rival_guild_state


SAVE_DIR = Path("saves")
DEFAULT_SAVE_PATH = SAVE_DIR / "save_slot_1.json"


def item_to_dict(item: Item) -> Dict:
    return {
        "name": item.name,
        "slot": item.slot,
        "stat_bonuses": item.stat_bonuses,
        "value": item.value,
        "rarity": item.rarity,
        "damage_type_bonus": item.damage_type_bonus,
        "enemy_type_bonus": item.enemy_type_bonus,
        "enemy_type_resistance": item.enemy_type_resistance,
        "class_restrictions": item.class_restrictions,
        "enemy_affinity": item.enemy_affinity,
    }


def item_from_dict(data: Dict) -> Item:
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

def hero_to_dict(hero: Hero) -> Dict:
    from systems.hero_progression import progression_to_dict, ensure_progression_fields

    ensure_progression_fields(hero)

    return {
        "name": hero.name,
        "hero_class": hero.hero_class,
        "age": hero.age,
        "level": hero.level,
        "xp": hero.xp,
        "stats": hero.stats,
        "signing_bonus": hero.signing_bonus,
        "wage_per_year": hero.wage_per_year,
        "contract_years": hero.contract_years,
        "specialty": hero.specialty,
        "growth_rate": hero.growth_rate,
        "contract_attitude": hero.contract_attitude,
        "equipment": {slot: item_to_dict(item) for slot, item in hero.equipment.items()},
        "injured_years_remaining": hero.injured_years_remaining,
        "wound_history": hero.wound_history,
        "current_health": hero.current_health,
        "debt": hero.debt,
        "is_temporary_survivor": hero.is_temporary_survivor,
        "satisfaction": getattr(hero, "satisfaction", 80),
        "participated_this_cycle": getattr(hero, "participated_this_cycle", False),
        "subclass": getattr(hero, "subclass", None),
        "special_ability": getattr(hero, "special_ability", None),
        "progression": progression_to_dict(hero),
    }

def hero_from_dict(data: Dict) -> Hero:
    from systems.hero_progression import apply_progression_from_dict, ensure_progression_fields

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
        contract_attitude=data.get("contract_attitude", "Practical"),
        equipment={slot: item_from_dict(item_data) for slot, item_data in data.get("equipment", {}).items()},
        injured_years_remaining=int(data.get("injured_years_remaining", 0)),
        wound_history=list(data.get("wound_history", [])),
        current_health=data.get("current_health"),
        debt=int(data.get("debt", 0)),
        is_temporary_survivor=bool(data.get("is_temporary_survivor", False)),
        satisfaction=int(data.get("satisfaction", 80)),
        participated_this_cycle=bool(data.get("participated_this_cycle", False)),
        subclass=data.get("subclass"),
        special_ability=data.get("special_ability"),
    )

    ensure_progression_fields(hero)
    apply_progression_from_dict(hero, data.get("progression"))

    return hero

def dungeon_to_dict(dungeon: Dungeon) -> Dict:
    return {
        "name": dungeon.name,
        "difficulty": dungeon.difficulty,
        "years_to_complete": dungeon.years_to_complete,
        "stages": dungeon.stages,
        "enemy_power": dungeon.enemy_power,
        "enemy_type": getattr(dungeon, "enemy_type", "Beasts"),
        "loot_min": dungeon.loot_min,
        "loot_max": dungeon.loot_max,
        "xp_reward": dungeon.xp_reward,
        "minor_wound_chance": dungeon.minor_wound_chance,
        "mortal_wound_chance": dungeon.mortal_wound_chance,
        "death_chance": dungeon.death_chance,
        "item_drop_chance": dungeon.item_drop_chance,
    }


def dungeon_from_dict(data: Dict) -> Dungeon:
    return Dungeon(
        name=data["name"],
        difficulty=int(data["difficulty"]),
        years_to_complete=int(data["years_to_complete"]),
        stages=int(data.get("stages", data["years_to_complete"])),
        enemy_power=int(data["enemy_power"]),
        enemy_type=data.get("enemy_type", "Beasts"),
        loot_min=int(data["loot_min"]),
        loot_max=int(data["loot_max"]),
        xp_reward=int(data["xp_reward"]),
        minor_wound_chance=float(data["minor_wound_chance"]),
        mortal_wound_chance=float(data["mortal_wound_chance"]),
        death_chance=float(data["death_chance"]),
        item_drop_chance=float(data["item_drop_chance"]),
    )


def reputation_to_dict(reputation: ManagerReputation) -> Dict:
    return {
        "overall": reputation.overall,
        "reliability": reputation.reliability,
        "safety": reputation.safety,
        "development": reputation.development,
        "protector": reputation.protector,
        "warrior": reputation.warrior,
        "rogue": reputation.rogue,
        "cleric": reputation.cleric,
        "mage": reputation.mage,
        "history": reputation.history,
    }


def reputation_from_dict(data: Dict) -> ManagerReputation:
    return ManagerReputation(
        overall=int(data.get("overall", 0)),
        reliability=int(data.get("reliability", 0)),
        safety=int(data.get("safety", 0)),
        development=int(data.get("development", 0)),
        protector=int(data.get("protector", 0)),
        warrior=int(data.get("warrior", 0)),
        rogue=int(data.get("rogue", 0)),
        cleric=int(data.get("cleric", 0)),
        mage=int(data.get("mage", 0)),
        history=list(data.get("history", [])),
    )


def bereavement_to_dict(payment: BereavementPayment) -> Dict:
    return {
        "hero_name": payment.hero_name,
        "amount": payment.amount,
    }


def bereavement_from_dict(data: Dict) -> BereavementPayment:
    return BereavementPayment(
        hero_name=data["hero_name"],
        amount=int(data["amount"]),
    )


def rival_guild_to_dict(guild: Dict) -> Dict:
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


def rival_guild_from_dict(data: Dict) -> Dict:
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


def contract_offer_to_dict(offer: Dict) -> Dict:
    return {
        "hero_name": offer.get("hero_name", ""),
        "offered_campaigns": int(offer.get("offered_campaigns", 1)),
        "offered_signing_fee": int(offer.get("offered_signing_fee", 25)),
    }


def contract_offer_from_dict(data: Dict) -> Dict:
    return {
        "hero_name": data.get("hero_name", ""),
        "offered_campaigns": int(data.get("offered_campaigns", 1)),
        "offered_signing_fee": int(data.get("offered_signing_fee", 25)),
    }


def campaign_runtime_to_dict(runtime: CampaignRuntime | None):
    if runtime is None:
        return None
    return runtime.to_dict()


def campaign_runtime_from_dict(data):
    if not data:
        return None
    return CampaignRuntime.from_dict(data)


def game_state_to_dict(state: GameState) -> Dict:
    ensure_rival_guild_state(state)

    return {
        "version": 9,
        "expedition": state.expedition,
        "year": state.year,
        "gold": state.gold,
        "roster": [hero_to_dict(hero) for hero in state.roster],
        "available_contracts": [hero_to_dict(hero) for hero in state.available_contracts],
        "inventory": [item_to_dict(item) for item in state.inventory],
        "dungeons": [dungeon_to_dict(dungeon) for dungeon in state.dungeons],
        "retired_heroes": [hero_to_dict(hero) for hero in state.retired_heroes],
        "fallen_heroes": [hero_to_dict(hero) for hero in state.fallen_heroes],
        "reputation": reputation_to_dict(state.reputation),
        "pending_bereavement_payments": [
            bereavement_to_dict(payment) for payment in state.pending_bereavement_payments
        ],
        "guild_upgrades": guild_upgrades_to_dict(state.guild_upgrades),
        "rival_guilds": [rival_guild_to_dict(guild) for guild in state.rival_guilds],
        "contract_offers": [contract_offer_to_dict(offer) for offer in state.contract_offers],
        "renewal_offers": [contract_offer_to_dict(offer) for offer in state.renewal_offers],
        "contract_round": int(state.contract_round),
        "market_history": list(state.market_history),
        "campaign_runtime": campaign_runtime_to_dict(getattr(state, "campaign_runtime", None)),
    }


def game_state_from_dict(data: Dict) -> GameState:
    state = GameState(
        expedition=int(data["expedition"]),
        year=int(data["year"]),
        gold=int(data["gold"]),
        roster=[hero_from_dict(hero_data) for hero_data in data.get("roster", [])],
        available_contracts=[
            hero_from_dict(hero_data) for hero_data in data.get("available_contracts", [])
        ],
        inventory=[item_from_dict(item_data) for item_data in data.get("inventory", [])],
        dungeons=[dungeon_from_dict(dungeon_data) for dungeon_data in data.get("dungeons", [])],
        retired_heroes=[hero_from_dict(hero_data) for hero_data in data.get("retired_heroes", [])],
        fallen_heroes=[hero_from_dict(hero_data) for hero_data in data.get("fallen_heroes", [])],
        reputation=reputation_from_dict(data.get("reputation", {})),
        pending_bereavement_payments=[
            bereavement_from_dict(payment_data)
            for payment_data in data.get("pending_bereavement_payments", [])
        ],
        guild_upgrades=guild_upgrades_from_dict(data.get("guild_upgrades")),
        rival_guilds=[rival_guild_from_dict(guild_data) for guild_data in data.get("rival_guilds", [])],
        contract_offers=[contract_offer_from_dict(offer_data) for offer_data in data.get("contract_offers", [])],
        renewal_offers=[contract_offer_from_dict(offer_data) for offer_data in data.get("renewal_offers", [])],
        contract_round=int(data.get("contract_round", 1)),
        market_history=list(data.get("market_history", [])),
        campaign_runtime=campaign_runtime_from_dict(data.get("campaign_runtime")),
    )

    ensure_rival_guild_state(state)
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