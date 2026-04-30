from copy import deepcopy
from typing import Dict, List, Optional

from hero_generator import generate_fallback_contract_market


RIVAL_GUILD_DEFINITIONS: List[Dict] = [
    {
        "name": "Iron Banner Company",
        "style": "Aggressive Buyers",
        "wealth_bias": 10,
        "aggression": 12,
        "prestige": 4,
        "rookie_interest": -4,
        "class_preference": "Warrior",
        "tagline": "Pays hard for proven steel.",
    },
    {
        "name": "Lantern Accord",
        "style": "Prestige Seekers",
        "wealth_bias": 4,
        "aggression": 6,
        "prestige": 12,
        "rookie_interest": 0,
        "class_preference": "Cleric",
        "tagline": "Prefers reputable, disciplined talent.",
    },
    {
        "name": "Ashen Hall",
        "style": "Elite Hunters",
        "wealth_bias": 8,
        "aggression": 8,
        "prestige": 10,
        "rookie_interest": -8,
        "class_preference": "Mage",
        "tagline": "Targets rare and high-upside heroes.",
    },
    {
        "name": "Mosshound Lodge",
        "style": "Rookie Developers",
        "wealth_bias": -4,
        "aggression": 3,
        "prestige": 1,
        "rookie_interest": 14,
        "class_preference": "Rogue",
        "tagline": "Builds cheap talent patiently.",
    },
    {
        "name": "Golden Stag Syndicate",
        "style": "Rich Opportunists",
        "wealth_bias": 14,
        "aggression": 5,
        "prestige": 6,
        "rookie_interest": 2,
        "class_preference": None,
        "tagline": "Can outbid almost anyone on a whim.",
    },
]

MARKET_HISTORY_LIMIT = 60
RECENT_PICKUPS_LIMIT = 10


def ensure_rival_guild_state(state) -> None:
    if not hasattr(state, "rival_guilds") or not isinstance(getattr(state, "rival_guilds"), list):
        state.rival_guilds = []

    if not hasattr(state, "market_history") or not isinstance(getattr(state, "market_history"), list):
        state.market_history = []

    existing_names = {
        guild.get("name")
        for guild in state.rival_guilds
        if isinstance(guild, dict)
    }

    for definition in RIVAL_GUILD_DEFINITIONS:
        if definition["name"] in existing_names:
            continue

        guild_state = deepcopy(definition)
        guild_state["roster"] = []
        guild_state["total_signings"] = 0
        guild_state["recent_pickups"] = []
        state.rival_guilds.append(guild_state)

    for guild in state.rival_guilds:
        guild.setdefault("name", "Unknown Rival")
        guild.setdefault("style", "Unknown")
        guild.setdefault("wealth_bias", 0)
        guild.setdefault("aggression", 0)
        guild.setdefault("prestige", 0)
        guild.setdefault("rookie_interest", 0)
        guild.setdefault("class_preference", None)
        guild.setdefault("tagline", "")
        guild.setdefault("roster", [])
        guild.setdefault("total_signings", 0)
        guild.setdefault("recent_pickups", [])


def rival_guilds(state) -> List[Dict]:
    ensure_rival_guild_state(state)
    return state.rival_guilds


def rival_guild_by_name(state, name: str) -> Optional[Dict]:
    ensure_rival_guild_state(state)

    for guild in state.rival_guilds:
        if guild.get("name") == name:
            return guild

    return None


def add_market_history_entry(state, text: str) -> None:
    ensure_rival_guild_state(state)

    if not text:
        return

    state.market_history.append(text)
    if len(state.market_history) > MARKET_HISTORY_LIMIT:
        state.market_history = state.market_history[-MARKET_HISTORY_LIMIT:]


def recent_market_history(state, limit: int = 12) -> List[str]:
    ensure_rival_guild_state(state)
    return list(state.market_history[-limit:])


def add_hero_to_rival_guild(state, guild_name: str, hero) -> None:
    guild = rival_guild_by_name(state, guild_name)
    if guild is None:
        return

    if any(existing.name == hero.name for existing in guild["roster"]):
        return

    guild["roster"].append(hero)
    guild["total_signings"] += 1
    guild["recent_pickups"].append(hero.name)

    if len(guild["recent_pickups"]) > RECENT_PICKUPS_LIMIT:
        guild["recent_pickups"] = guild["recent_pickups"][-RECENT_PICKUPS_LIMIT:]


def guild_power(guild: Dict) -> int:
    total = 0
    for hero in guild.get("roster", []):
        combat_power_fn = getattr(hero, "combat_power", None)
        if callable(combat_power_fn):
            total += combat_power_fn()
    return total


def rival_interest_reason(guild: Dict, hero) -> str:
    reasons: List[str] = []

    if guild.get("class_preference") == hero.hero_class:
        reasons.append(f"prefers {hero.hero_class}s")

    if getattr(hero, "is_developmental", False) and guild.get("rookie_interest", 0) > 0:
        reasons.append("likes developmental talent")

    if getattr(hero, "market_tier", "Standard") == "Elite" and guild.get("prestige", 0) >= 8:
        reasons.append("hunts elite talent")

    if guild.get("wealth_bias", 0) >= 10:
        reasons.append("can spend aggressively")

    if not reasons:
        reasons.append("is active in this market")

    return ", ".join(reasons[:2])


def _add_hero_to_market_if_missing(state, hero) -> None:
    for existing in state.available_contracts:
        if existing.name == hero.name:
            return
    state.available_contracts.append(hero)


def advance_rival_guilds(state, years_passed: int = 2) -> List[str]:
    ensure_rival_guild_state(state)

    messages: List[str] = []

    for guild in state.rival_guilds:
        roster = list(guild.get("roster", []))
        remaining_roster = []

        for hero in roster:
            old_age = hero.age
            hero.age += years_passed

            if hero.contract_years > 0:
                hero.contract_years = max(0, hero.contract_years - 1)

            retired = False
            should_retire = getattr(hero, "should_retire", None)
            if callable(should_retire):
                retired = bool(should_retire())

            if retired:
                messages.append(f"{hero.name} retired from {guild['name']}.")
                add_market_history_entry(state, f"{hero.name} retired from {guild['name']}.")
                continue

            if hero.contract_years <= 0:
                _add_hero_to_market_if_missing(state, hero)
                messages.append(f"{hero.name} left {guild['name']} after contract expiry.")
                add_market_history_entry(state, f"{hero.name} left {guild['name']} after contract expiry.")
                continue

            if old_age != hero.age:
                remaining_roster.append(hero)
            else:
                remaining_roster.append(hero)

        guild["roster"] = remaining_roster

        target_size = 3 + max(0, guild.get("prestige", 0) // 3)
        target_size = min(target_size, 8)
        needed = max(0, target_size - len(guild["roster"]))
        if needed <= 0:
            continue

        prospects = generate_fallback_contract_market(state, count=needed)
        for hero in prospects[:needed]:
            if any(existing.name == hero.name for existing in guild["roster"]):
                continue

            guild["roster"].append(hero)
            guild["total_signings"] += 1
            guild["recent_pickups"].append(hero.name)
            if len(guild["recent_pickups"]) > RECENT_PICKUPS_LIMIT:
                guild["recent_pickups"] = guild["recent_pickups"][-RECENT_PICKUPS_LIMIT:]

            messages.append(f"{guild['name']} added {hero.name} to strengthen its roster.")
            add_market_history_entry(state, f"{guild['name']} added {hero.name} to strengthen its roster.")

    return messages