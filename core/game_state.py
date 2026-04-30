from dataclasses import dataclass, field
from typing import Dict, List, Optional

from data_loader import load_dungeons, load_items
from hero_generator import generate_contract_market
from manager_reputation import ManagerReputation
from models import Dungeon, Hero, Item
from systems.campaign.campaign_runtime import create_campaign_runtime
from systems.campaign.campaign_models import CampaignRuntime
from systems.guild_upgrades import GuildUpgrades
from systems.rival_guilds import ensure_rival_guild_state


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
    campaign_runtime: Optional[CampaignRuntime] = None


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


def refresh_contract_market(state: GameState) -> None:
    state.available_contracts = generate_contract_market(state)


def campaign_is_active(state: GameState) -> bool:
    runtime = getattr(state, "campaign_runtime", None)
    return runtime is not None and bool(getattr(runtime, "active", False))


def start_campaign_runtime(state: GameState, max_spawns: int = 18):
    state.campaign_runtime = create_campaign_runtime(max_spawns=max_spawns)
    return state.campaign_runtime


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
        contract_offers=[],
        renewal_offers=[],
        contract_round=1,
        market_history=[],
        campaign_runtime=None,
    )
    refresh_contract_market(state)
    ensure_rival_guild_state(state)
    return state