from dataclasses import dataclass, field
from typing import List

from data_loader import load_dungeons, load_items
from hero_generator import generate_contract_market
from manager_reputation import ManagerReputation
from models import Dungeon, Hero, Item
from systems.guild_upgrades import GuildUpgrades


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


def create_game() -> GameState:
    state = GameState(
        expedition=1,
        year=1,
        gold=500,
        roster=[],
        available_contracts=[],
        inventory=[],
        dungeons=create_dungeons(),
    )
    refresh_contract_market(state)
    return state