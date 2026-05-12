"""
systems/guild/guild_upgrades.py

Guild upgrade system — branching capability and identity tree.

Design intent (GDD / TDD):
  Upgrades define who the guild becomes, not just what numbers it has.
  The tree has two kinds of nodes:

  Capability upgrades — infrastructure that any guild buys: lodging,
  training, recruitment, market access, stipend, mission scope.
  These are mostly linear within their branch.

  Doctrine upgrades — the identity fork.  Exactly one of three doctrines
  can be chosen.  Choosing one soft-locks the other two and opens deeper
  upgrades on that path.  This is the core "what kind of guild are you?"
  decision.

    Militant  — leans into combat power, mission difficulty, injury recovery.
    Merchant  — leans into market access, stipend, item quality.
    Scholarly — leans into hero development, training depth, recruitment quality.

  Some upgrades carry a tradeoff: a positive effect paired with a cost or
  restriction.  These are flagged with `drawback` so the UI can surface them.

Save / load:
  GuildUpgrades now tracks purchased_upgrade_ids as a set so that the
  "requires" check can gate on what has already been bought, enabling
  proper tree dependencies without the fragile lambda equality checks.
  Backward-compat: old saves without this field default to deriving the
  set from the existing scalar fields via _infer_purchased_from_legacy().
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# GuildUpgrades state
# ---------------------------------------------------------------------------

@dataclass
class GuildUpgrades:
    # -- Capability fields (read by many systems, must stay stable) ----------
    roster_capacity: int = 1
    unlocked_classes: List[str] = field(default_factory=lambda: ["Warrior"])
    recruit_level_cap: int = 1
    market_unlocked: bool = False
    market_rarity_cap: str = "Common"
    mission_difficulty_cap: int = 1
    crown_stipend: int = 50
    training_hall_level: int = 0

    # -- New fields ----------------------------------------------------------
    purchased_upgrade_ids: Set[str] = field(default_factory=set)
    # Tracks every upgrade that has been bought.  This is the canonical
    # source for "requires" checks — scalar fields above are still updated
    # for backward compat with systems that read them directly.

    doctrine: str = ""
    # "", "militant", "merchant", or "scholarly".
    # Set when the player buys a doctrine upgrade.  Soft-locks the other two.

    equip_capacity_bonus: int = 0
    # Guild-wide equipment slot bonus applied to all heroes.
    # Currently only granted by the Militant doctrine path.

    injury_recovery_bonus: int = 0
    # Reduces injury year count by this many when cycle advances.
    # Granted by Militant path.

    market_refresh_discount: int = 0
    # Gold discount on market refreshes.  Granted by Merchant path.

    xp_bonus_percent: int = 0
    # Percentage bonus to all XP gains.  Granted by Scholarly path.

    def has(self, upgrade_id: str) -> bool:
        return upgrade_id in self.purchased_upgrade_ids

    def doctrine_locked(self) -> bool:
        return bool(self.doctrine)

    def doctrine_label(self) -> str:
        return {
            "militant":  "Militant",
            "merchant":  "Merchant",
            "scholarly": "Scholarly",
        }.get(self.doctrine, "Undecided")


# ---------------------------------------------------------------------------
# Upgrade node definition
# ---------------------------------------------------------------------------

class UpgradeNode:
    """
    A single purchasable upgrade.

    Fields
    ------
    id          Unique string key.
    name        Display name.
    branch      Which branch this belongs to (for grouping in the UI).
    cost        Gold cost.
    description Effect description shown to the player.
    drawback    Optional negative tradeoff description.  None = pure upside.
    requires    List of upgrade_ids that must be purchased first.
    doctrine_requires  If set, this node is only available if the guild has
                       chosen this doctrine (or no doctrine yet for the fork
                       node itself).
    doctrine_locks     If set, buying this node sets the guild doctrine to
                       this value and soft-locks the others.
    apply       Function (upgrades) -> None that mutates GuildUpgrades state.
    """

    def __init__(
        self,
        id: str,
        name: str,
        branch: str,
        cost: int,
        description: str,
        apply,
        requires: Optional[List[str]] = None,
        drawback: Optional[str] = None,
        doctrine_requires: Optional[str] = None,
        doctrine_locks: Optional[str] = None,
    ):
        self.id                = id
        self.name              = name
        self.branch            = branch
        self.cost              = cost
        self.description       = description
        self.drawback          = drawback
        self.requires          = requires or []
        self.doctrine_requires = doctrine_requires
        self.doctrine_locks    = doctrine_locks
        self.apply_fn          = apply

    def is_available(self, upgrades: GuildUpgrades) -> bool:
        """Return True if this upgrade can currently be purchased."""
        if upgrades.has(self.id):
            return False  # Already bought.

        for req in self.requires:
            if not upgrades.has(req):
                return False

        if self.doctrine_requires is not None:
            if upgrades.doctrine and upgrades.doctrine != self.doctrine_requires:
                return False  # Doctrine locked to something else.

        if self.doctrine_locks and upgrades.doctrine_locked():
            if upgrades.doctrine != self.doctrine_locks:
                return False  # Would lock to a different doctrine.

        return True

    def purchase(self, upgrades: GuildUpgrades) -> None:
        upgrades.purchased_upgrade_ids.add(self.id)
        if self.doctrine_locks:
            upgrades.doctrine = self.doctrine_locks
        self.apply_fn(upgrades)


# ---------------------------------------------------------------------------
# Upgrade tree definition
# ---------------------------------------------------------------------------

def _u(id, name, branch, cost, description, apply, **kwargs) -> UpgradeNode:
    return UpgradeNode(id=id, name=name, branch=branch, cost=cost,
                       description=description, apply=apply, **kwargs)


UPGRADE_TREE: List[UpgradeNode] = [

    # -----------------------------------------------------------------------
    # Branch: Lodging  (roster capacity)
    # -----------------------------------------------------------------------
    _u("lodging_2", "Expand Lodging I", "Lodging", 150,
       "Increase guild roster capacity to 2 heroes.",
       lambda u: setattr(u, "roster_capacity", 2)),

    _u("lodging_4", "Expand Lodging II", "Lodging", 300,
       "Increase guild roster capacity to 4 heroes.",
       lambda u: setattr(u, "roster_capacity", 4),
       requires=["lodging_2"]),

    _u("lodging_6", "Expand Lodging III", "Lodging", 600,
       "Increase guild roster capacity to 6 heroes.",
       lambda u: setattr(u, "roster_capacity", 6),
       requires=["lodging_4"]),

    # -----------------------------------------------------------------------
    # Branch: Training Hall
    # -----------------------------------------------------------------------
    _u("training_1", "Build Training Hall", "Training", 175,
       "Unlock paid hero training during the management phase.",
       lambda u: setattr(u, "training_hall_level", 1)),

    _u("training_2", "Improve Training Hall I", "Training", 350,
       "Training sessions grant more experience per session.",
       lambda u: setattr(u, "training_hall_level", 2),
       requires=["training_1"]),

    _u("training_3", "Improve Training Hall II", "Training", 700,
       "Further improve training gains. Unlocks specialisation paths.",
       lambda u: setattr(u, "training_hall_level", 3),
       requires=["training_2"]),

    # -----------------------------------------------------------------------
    # Branch: Recruitment
    # -----------------------------------------------------------------------
    _u("recruit_rogue", "Build Rogue Den", "Recruitment", 200,
       "Rogues can appear in the hiring market.",
       lambda u: u.unlocked_classes.append("Rogue")
       if "Rogue" not in u.unlocked_classes else None),

    _u("recruit_cleric", "Build Shrine", "Recruitment", 275,
       "Clerics can appear in the hiring market.",
       lambda u: u.unlocked_classes.append("Cleric")
       if "Cleric" not in u.unlocked_classes else None),

    _u("recruit_mage", "Build Arcane Study", "Recruitment", 400,
       "Mages can appear in the hiring market.",
       lambda u: u.unlocked_classes.append("Mage")
       if "Mage" not in u.unlocked_classes else None),

    _u("recruit_level_3", "Improve Recruitment I", "Recruitment", 250,
       "Recruits may appear up to level 3.",
       lambda u: setattr(u, "recruit_level_cap", 3)),

    _u("recruit_level_5", "Improve Recruitment II", "Recruitment", 500,
       "Recruits may appear up to level 5.",
       lambda u: setattr(u, "recruit_level_cap", 5),
       requires=["recruit_level_3"]),

    # -----------------------------------------------------------------------
    # Branch: Market
    # -----------------------------------------------------------------------
    _u("market_open", "Open Guild Market", "Market", 200,
       "Unlock the item market where the guild can buy equipment.",
       lambda u: setattr(u, "market_unlocked", True)),

    _u("market_uncommon", "Stock Uncommon Wares", "Market", 300,
       "Uncommon items can appear in the market.",
       lambda u: setattr(u, "market_rarity_cap", "Uncommon"),
       requires=["market_open"]),

    _u("market_rare", "Stock Rare Wares", "Market", 550,
       "Rare items can appear in the market.",
       lambda u: setattr(u, "market_rarity_cap", "Rare"),
       requires=["market_uncommon"]),

    # -----------------------------------------------------------------------
    # Branch: Operations  (stipend + mission difficulty)
    # -----------------------------------------------------------------------
    _u("stipend_100", "Petition the Crown I", "Operations", 250,
       "Increase the Crown stipend to 100g per campaign.",
       lambda u: setattr(u, "crown_stipend", 100)),

    _u("stipend_150", "Petition the Crown II", "Operations", 450,
       "Increase the Crown stipend to 150g per campaign.",
       lambda u: setattr(u, "crown_stipend", 150),
       requires=["stipend_100"]),

    _u("mission_2", "Scout Dangerous Roads I", "Operations", 225,
       "Unlock difficulty 2 missions.",
       lambda u: setattr(u, "mission_difficulty_cap", 2)),

    _u("mission_3", "Scout Dangerous Roads II", "Operations", 450,
       "Unlock difficulty 3 missions.",
       lambda u: setattr(u, "mission_difficulty_cap", 3),
       requires=["mission_2"]),

    # -----------------------------------------------------------------------
    # Branch: Doctrine  (identity fork — choose one path)
    #
    # The three doctrine nodes are mutually exclusive.  Buying any one sets
    # upgrades.doctrine and prevents the other two from being purchased.
    # Deeper doctrine nodes are only visible after the fork is chosen.
    # -----------------------------------------------------------------------

    _u("doctrine_militant", "Militant Doctrine", "Doctrine", 500,
       "The guild prioritises combat strength and endurance. "
       "Heroes recover from injuries one year faster. "
       "Unlocks further Militant upgrades.",
       lambda u: setattr(u, "injury_recovery_bonus", 1),
       drawback="Locks Merchant and Scholarly doctrine paths permanently.",
       doctrine_locks="militant"),

    _u("doctrine_merchant", "Merchant Doctrine", "Doctrine", 500,
       "The guild prioritises wealth and market access. "
       "Market refreshes cost 10g less. "
       "Unlocks further Merchant upgrades.",
       lambda u: setattr(u, "market_refresh_discount", 10),
       drawback="Locks Militant and Scholarly doctrine paths permanently.",
       doctrine_locks="merchant"),

    _u("doctrine_scholarly", "Scholarly Doctrine", "Doctrine", 500,
       "The guild prioritises knowledge and hero development. "
       "All heroes gain +10% XP from missions. "
       "Unlocks further Scholarly upgrades.",
       lambda u: setattr(u, "xp_bonus_percent", 10),
       drawback="Locks Militant and Merchant doctrine paths permanently.",
       doctrine_locks="scholarly"),

    # -----------------------------------------------------------------------
    # Militant path (requires militant doctrine)
    # -----------------------------------------------------------------------
    _u("militant_armory", "Build Armory", "Militant", 400,
       "Each hero can equip one additional item (equip capacity +1).",
       lambda u: setattr(u, "equip_capacity_bonus", u.equip_capacity_bonus + 1),
       requires=["doctrine_militant"],
       doctrine_requires="militant"),

    _u("militant_infirmary", "Build Infirmary", "Militant", 350,
       "Injured heroes recover two years faster instead of one.",
       lambda u: setattr(u, "injury_recovery_bonus", 2),
       requires=["doctrine_militant"],
       doctrine_requires="militant"),

    _u("militant_veteran_bonus", "Veteran's Hall", "Militant", 600,
       "Veteran and Elder heroes deal 10% more damage on missions.",
       lambda u: None,  # Consumed by task_scoring when implemented.
       requires=["militant_armory"],
       doctrine_requires="militant"),

    # -----------------------------------------------------------------------
    # Merchant path (requires merchant doctrine)
    # -----------------------------------------------------------------------
    _u("merchant_contacts", "Trade Contacts", "Merchant", 350,
       "Market refreshes cost 20g less (stacks with doctrine bonus).",
       lambda u: setattr(u, "market_refresh_discount", u.market_refresh_discount + 10),
       requires=["doctrine_merchant"],
       doctrine_requires="merchant"),

    _u("merchant_epic", "Stock Epic Wares", "Merchant", 700,
       "Epic items can appear in the market.",
       lambda u: setattr(u, "market_rarity_cap", "Epic"),
       requires=["doctrine_merchant", "market_rare"],
       doctrine_requires="merchant"),

    _u("merchant_stipend", "Crown Partnership", "Merchant", 500,
       "Increase the Crown stipend to 200g per campaign.",
       lambda u: setattr(u, "crown_stipend", 200),
       requires=["merchant_contacts", "stipend_150"],
       doctrine_requires="merchant"),

    # -----------------------------------------------------------------------
    # Scholarly path (requires scholarly doctrine)
    # -----------------------------------------------------------------------
    _u("scholarly_library", "Build Library", "Scholarly", 350,
       "Heroes gain +20% XP from missions (stacks with doctrine bonus).",
       lambda u: setattr(u, "xp_bonus_percent", u.xp_bonus_percent + 10),
       requires=["doctrine_scholarly"],
       doctrine_requires="scholarly"),

    _u("scholarly_recruits", "Scholar's Network", "Scholarly", 450,
       "Recruits may appear up to level 7.",
       lambda u: setattr(u, "recruit_level_cap", 7),
       requires=["doctrine_scholarly", "recruit_level_5"],
       doctrine_requires="scholarly"),

    _u("scholarly_mastery", "Mastery Programme", "Scholarly", 600,
       "Training sessions grant an additional training point.",
       lambda u: None,  # Consumed by hero_training when implemented.
       requires=["scholarly_library", "training_3"],
       doctrine_requires="scholarly"),
]


# ---------------------------------------------------------------------------
# Index for fast lookup
# ---------------------------------------------------------------------------

_UPGRADE_BY_ID: Dict[str, UpgradeNode] = {node.id: node for node in UPGRADE_TREE}

BRANCH_ORDER = ["Lodging", "Training", "Recruitment", "Market",
                "Operations", "Doctrine", "Militant", "Merchant", "Scholarly"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def available_upgrades(upgrades: GuildUpgrades) -> List[UpgradeNode]:
    """Return all nodes that are currently purchasable."""
    return [node for node in UPGRADE_TREE if node.is_available(upgrades)]


def all_upgrades_by_branch(upgrades: GuildUpgrades) -> Dict[str, List[UpgradeNode]]:
    """
    Return every node grouped by branch, for tree display in the scene.
    Each node carries its own is_available() state so the UI can dim locked
    or already-purchased nodes while still showing the full tree shape.
    """
    grouped: Dict[str, List[UpgradeNode]] = {b: [] for b in BRANCH_ORDER}
    for node in UPGRADE_TREE:
        branch = node.branch if node.branch in grouped else "Doctrine"
        grouped[branch].append(node)
    return grouped


def get_upgrade(upgrade_id: str) -> Optional[UpgradeNode]:
    return _UPGRADE_BY_ID.get(upgrade_id)


def buy_upgrade(state, upgrade_id: str) -> str:
    node = _UPGRADE_BY_ID.get(upgrade_id)
    if node is None:
        return "Unknown upgrade."

    upgrades = state.guild_upgrades

    if not node.is_available(upgrades):
        if upgrades.has(upgrade_id):
            return f"{node.name} has already been purchased."
        return f"{node.name} is not currently available."

    if state.gold < node.cost:
        return f"Not enough gold. {node.name} costs {node.cost}g."

    state.gold -= node.cost
    node.purchase(upgrades)
    return f"Purchased: {node.name}."


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def guild_upgrades_to_dict(upgrades: GuildUpgrades) -> dict:
    return {
        # Legacy scalar fields — kept for backward compat.
        "roster_capacity":       upgrades.roster_capacity,
        "unlocked_classes":      list(upgrades.unlocked_classes),
        "recruit_level_cap":     upgrades.recruit_level_cap,
        "market_unlocked":       upgrades.market_unlocked,
        "market_rarity_cap":     upgrades.market_rarity_cap,
        "mission_difficulty_cap": upgrades.mission_difficulty_cap,
        "crown_stipend":         upgrades.crown_stipend,
        "training_hall_level":   upgrades.training_hall_level,
        # New fields.
        "purchased_upgrade_ids": sorted(upgrades.purchased_upgrade_ids),
        "doctrine":              upgrades.doctrine,
        "equip_capacity_bonus":  upgrades.equip_capacity_bonus,
        "injury_recovery_bonus": upgrades.injury_recovery_bonus,
        "market_refresh_discount": upgrades.market_refresh_discount,
        "xp_bonus_percent":      upgrades.xp_bonus_percent,
    }


def guild_upgrades_from_dict(data: dict | None) -> GuildUpgrades:
    if not data:
        return GuildUpgrades()

    roster_capacity = data.get("roster_capacity", data.get("party_slots", 1))

    upgrades = GuildUpgrades(
        roster_capacity=int(roster_capacity),
        unlocked_classes=list(data.get("unlocked_classes", ["Warrior"])),
        recruit_level_cap=int(data.get("recruit_level_cap", 1)),
        market_unlocked=bool(data.get("market_unlocked", False)),
        market_rarity_cap=data.get("market_rarity_cap", "Common"),
        mission_difficulty_cap=int(data.get("mission_difficulty_cap", 1)),
        crown_stipend=int(data.get("crown_stipend", 50)),
        training_hall_level=int(data.get("training_hall_level", 0)),
        purchased_upgrade_ids=set(data.get("purchased_upgrade_ids", [])),
        doctrine=data.get("doctrine", ""),
        equip_capacity_bonus=int(data.get("equip_capacity_bonus", 0)),
        injury_recovery_bonus=int(data.get("injury_recovery_bonus", 0)),
        market_refresh_discount=int(data.get("market_refresh_discount", 0)),
        xp_bonus_percent=int(data.get("xp_bonus_percent", 0)),
    )

    # Migration: if this is an old save without purchased_upgrade_ids,
    # infer what was bought from the scalar fields so the tree renders
    # correctly without wiping progress.
    if not upgrades.purchased_upgrade_ids:
        upgrades.purchased_upgrade_ids = _infer_purchased_from_legacy(upgrades)

    return upgrades


def _infer_purchased_from_legacy(upgrades: GuildUpgrades) -> Set[str]:
    """
    Best-effort reconstruction of purchased_upgrade_ids from old scalar
    fields.  Used when loading a save that predates the new system.
    """
    ids: Set[str] = set()

    cap = upgrades.roster_capacity
    if cap >= 2: ids.add("lodging_2")
    if cap >= 4: ids.add("lodging_4")
    if cap >= 6: ids.add("lodging_6")

    th = upgrades.training_hall_level
    if th >= 1: ids.add("training_1")
    if th >= 2: ids.add("training_2")
    if th >= 3: ids.add("training_3")

    if "Rogue"  in upgrades.unlocked_classes: ids.add("recruit_rogue")
    if "Cleric" in upgrades.unlocked_classes: ids.add("recruit_cleric")
    if "Mage"   in upgrades.unlocked_classes: ids.add("recruit_mage")

    rlc = upgrades.recruit_level_cap
    if rlc >= 3: ids.add("recruit_level_3")
    if rlc >= 5: ids.add("recruit_level_5")

    if upgrades.market_unlocked: ids.add("market_open")

    rarity_order = ["Common", "Uncommon", "Rare", "Epic", "Legendary"]
    rarity_idx   = rarity_order.index(upgrades.market_rarity_cap) if upgrades.market_rarity_cap in rarity_order else 0
    if rarity_idx >= 1: ids.add("market_uncommon")
    if rarity_idx >= 2: ids.add("market_rare")

    stipend = upgrades.crown_stipend
    if stipend >= 100: ids.add("stipend_100")
    if stipend >= 150: ids.add("stipend_150")

    diff = upgrades.mission_difficulty_cap
    if diff >= 2: ids.add("mission_2")
    if diff >= 3: ids.add("mission_3")

    return ids