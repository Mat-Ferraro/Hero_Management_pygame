from dataclasses import dataclass, field
from typing import Any, Dict, List

from data_loader import load_dungeons, load_items
from hero_generator import generate_contract_market
from manager_reputation import ManagerReputation
from models import Dungeon, Hero, Item
from systems.guild_upgrades import GuildUpgrades
from systems.rival_guilds import ensure_rival_guild_state


SEASONAL_MARKET_POOL_SIZE = 30
MARKET_STAGE_MAX = 3


@dataclass
class BereavementPayment:
    hero_name: str
    amount: int


@dataclass
class GameState:
    expedition: int
    year: int
    gold: int
    roster: List[Hero]
    available_contracts: List[Hero]
    inventory: List[Item]
    dungeons: List[Dungeon]

    retired_heroes: List[Hero] = field(default_factory=list)
    fallen_heroes: List[Hero] = field(default_factory=list)
    reputation: ManagerReputation = field(default_factory=ManagerReputation)
    pending_bereavement_payments: List[BereavementPayment] = field(default_factory=list)
    guild_upgrades: GuildUpgrades = field(default_factory=GuildUpgrades)

    rival_guilds: List[Dict] = field(default_factory=list)

    contract_offers: List[Dict] = field(default_factory=list)
    renewal_offers: List[Dict] = field(default_factory=list)
    contract_round: int = 1
    market_history: List[str] = field(default_factory=list)

    seasonal_contract_pool: List[Hero] = field(default_factory=list)
    market_stage: int = 1
    market_stage_max: int = MARKET_STAGE_MAX
    market_cycle: int = 1
    market_fallback_open: bool = False
    market_closed: bool = False

    campaign_runtime: Any | None = None


def create_dungeons() -> List[Dungeon]:
    return load_dungeons()


def create_item_pool() -> List[Item]:
    return load_items()


def available_dungeons_for_state(state: GameState) -> List[Dungeon]:
    return [
        dungeon
        for dungeon in state.dungeons
        if dungeon.difficulty <= state.guild_upgrades.mission_difficulty_cap
    ]


def start_contract_market_cycle(state: GameState, pool_size: int = SEASONAL_MARKET_POOL_SIZE) -> None:
    state.contract_offers = []
    state.renewal_offers = []
    state.contract_round = 1
    state.market_stage = 1
    state.market_stage_max = MARKET_STAGE_MAX
    state.market_fallback_open = False
    state.market_closed = False

    full_pool = generate_contract_market(state, count=pool_size)
    state.seasonal_contract_pool = list(full_pool)
    state.available_contracts = list(full_pool)

    state.market_history.append(
        f"Opened hiring market cycle {state.market_cycle} with {len(full_pool)} total recruits."
    )


def retire_unclaimed_market_heroes(state: GameState) -> None:
    if not getattr(state, "available_contracts", []):
        state.seasonal_contract_pool = []
        state.market_closed = True
        return

    remaining = list(state.available_contracts)
    state.retired_heroes.extend(remaining)
    state.available_contracts = []
    state.seasonal_contract_pool = []
    state.market_closed = True

    state.market_history.append(
        f"{len(remaining)} unsigned hero(es) left the market and are out of circulation."
    )


def refresh_contract_market(state: GameState) -> None:
    if getattr(state, "available_contracts", []):
        retire_unclaimed_market_heroes(state)

    state.market_cycle += 1
    start_contract_market_cycle(state)


def campaign_is_active(state: GameState) -> bool:
    runtime = getattr(state, "campaign_runtime", None)
    if runtime is None:
        return False

    return bool(getattr(runtime, "is_active", False))


def start_campaign_runtime(state: GameState):
    from systems.campaign.campaign_runtime import CampaignRuntime

    runtime = getattr(state, "campaign_runtime", None)
    if runtime is not None and getattr(runtime, "is_active", False):
        return runtime

    runtime = CampaignRuntime()
    runtime.is_active = True
    state.campaign_runtime = runtime
    return runtime


def stop_campaign_runtime(state: GameState) -> None:
    runtime = getattr(state, "campaign_runtime", None)
    if runtime is None:
        return

    runtime.is_active = False


def clear_campaign_runtime(state: GameState) -> None:
    state.campaign_runtime = None


def create_game() -> GameState:
    state = GameState(
        expedition=1,
        year=1,
        gold=500,
        roster=[],
        available_contracts=[],
        inventory=[],
        dungeons=create_dungeons(),
        retired_heroes=[],
        fallen_heroes=[],
        reputation=ManagerReputation(),
        pending_bereavement_payments=[],
        guild_upgrades=GuildUpgrades(),
        rival_guilds=[],
        contract_offers=[],
        renewal_offers=[],
        contract_round=1,
        market_history=[],
        seasonal_contract_pool=[],
        market_stage=1,
        market_stage_max=MARKET_STAGE_MAX,
        market_cycle=1,
        market_fallback_open=False,
        market_closed=False,
        campaign_runtime=None,
    )

    ensure_rival_guild_state(state)
    start_contract_market_cycle(state)
    return state