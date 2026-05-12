"""
pygame_ui/scenes/guild_upgrades_scene.py

Guild upgrades scene — redesigned for the UpgradeNode branching system.

Key changes from the old scene:
  - Upgrade list now shows ALL nodes (available, purchased, locked) grouped
    by branch, so the player can see the full tree shape and plan ahead.
  - Row styles distinguish: purchasable (bright), already owned (green dim),
    locked by prerequisite (grey), locked by doctrine (orange dim).
  - The doctrine fork is highlighted prominently in the status panel.
  - Purchased and locked nodes cannot be selected for purchase.
  - Details panel shows drawback (if any), doctrine lock warning, and
    which prerequisites are still needed.
"""

import pygame

from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.ui_helpers import truncate_text
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.key_value_grid import KeyValueGrid
from pygame_ui.widgets.navigation_buttons import action_button, hub_button
from pygame_ui.widgets.resource_header import ResourceHeader
from pygame_ui.widgets.section_title import SectionTitle
from pygame_ui.widgets.status_chip import StatusChip
from pygame_ui.widgets.text_block import TextBlock
from pygame_ui.widgets.row_styles import draw_selectable_row
from pygame_ui.widgets.scrollable_list_panel import ScrollableListPanel
from systems.guild.guild_upgrades import (
    BRANCH_ORDER,
    UPGRADE_TREE,
    buy_upgrade,
    get_upgrade,
)


# Branches that are doctrine-gated — only show if doctrine chosen or it's the fork.
DOCTRINE_BRANCHES = {"Militant", "Merchant", "Scholarly"}
DOCTRINE_FORK_IDS = {"doctrine_militant", "doctrine_merchant", "doctrine_scholarly"}


class GuildUpgradesScene(SceneBase):

    def __init__(self, state, on_return_to_hub, on_save_game):
        super().__init__()

        self.state            = state
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game     = on_save_game

        self.status_message      = "Invest in your guild."
        self.selected_upgrade_id = None

        self.upgrades_panel = ScrollableListPanel(
            rect=(40, 150, 1060, 840),
            title="Upgrade Tree",
            row_height=66,
            row_gap=6,
            visible_rows=None,
            font=self.font,
            title_font=self.title_font,
            padding=16,
            title_height=64,
        )

        self.status_rect = (1140, 150, 720, 840)

    # ------------------------------------------------------------------
    # List building
    # ------------------------------------------------------------------

    def _visible_nodes(self):
        """
        Return all upgrade nodes the player should see, in branch order.
        Doctrine-path branches (Militant/Merchant/Scholarly) are only shown
        once a doctrine has been chosen — this keeps the list clean until
        the fork decision is made.
        """
        upgrades = self.state.guild_upgrades
        chosen_doctrine = getattr(upgrades, "doctrine", "")

        nodes = []
        for branch in BRANCH_ORDER:
            # Skip doctrine sub-branches until a doctrine is chosen.
            if branch in DOCTRINE_BRANCHES and not chosen_doctrine:
                continue
            # If a doctrine is chosen, only show the matching branch.
            if branch in DOCTRINE_BRANCHES and chosen_doctrine:
                if branch.lower() != chosen_doctrine:
                    continue

            branch_nodes = [n for n in UPGRADE_TREE if n.branch == branch]
            nodes.extend(branch_nodes)

        return nodes

    def _node_status(self, node):
        """
        Return one of: "available", "purchased", "locked_prereq",
        "locked_doctrine", "locked_gold".
        """
        upgrades = self.state.guild_upgrades

        if upgrades.has(node.id):
            return "purchased"

        # Check doctrine lock.
        if node.doctrine_locks and upgrades.doctrine_locked():
            if upgrades.doctrine != node.doctrine_locks:
                return "locked_doctrine"

        if node.doctrine_requires and upgrades.doctrine:
            if upgrades.doctrine != node.doctrine_requires:
                return "locked_doctrine"

        # Check prerequisites.
        for req in node.requires:
            if not upgrades.has(req):
                return "locked_prereq"

        # Check gold.
        if self.state.gold < node.cost:
            return "locked_gold"

        return "available"

    def sync_lists(self):
        self.upgrades_panel.set_items(self._visible_nodes())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def handle_event(self, event):
        self.sync_lists()
        if self.upgrades_panel.handle_event(event): return
        if self.handle_buttons_click(event, self.build_buttons()): return
        if self.is_left_click(event): self._handle_row_click(event.pos)

    def update(self, mouse_pos):
        super().update(mouse_pos)
        self.sync_lists()
        self.upgrades_panel.update(mouse_pos)

    def draw(self, screen):
        self.sync_lists()
        self.clear_screen(screen)
        self.draw_header(screen)
        self.upgrades_panel.draw(
            screen=screen,
            row_drawer=self.draw_upgrade_row,
            selected_item=self._selected_node(),
            empty_text="No upgrades available.",
        )
        self.draw_status_panel(screen)
        self.update_and_draw_buttons(screen, self.build_buttons())

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def draw_header(self, screen):
        upgrades = self.state.guild_upgrades
        doctrine = upgrades.doctrine_label() if hasattr(upgrades, "doctrine_label") else "Undecided"

        HeaderPanel(
            rect=(40, 30, 1840, 96),
            title="Guild Upgrades",
            stats="",
            status_message=self.status_message,
            stats_pos=(70, 70),
            status_pos=(1060, 108),
        ).draw(screen, self.title_font, self.header_font, self.font)

        ResourceHeader(
            resources=[
                ("Gold",     f"{self.state.gold}g"),
                ("Roster",   f"{len(self.state.roster)}/{upgrades.roster_capacity}"),
                ("Stipend",  f"{upgrades.crown_stipend}g"),
                ("Training", f"Lv {upgrades.training_hall_level}"),
                ("Doctrine", doctrine),
            ],
            spacing=185,
            item_max_width=170,
            font_size=24,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=False,
            value_bold=True,
        ).draw(screen, self.font, 60, 72)

    # ------------------------------------------------------------------
    # Row drawer
    # ------------------------------------------------------------------

    def draw_upgrade_row(self, screen, node, row_rect, is_selected, is_hovered):
        status = self._node_status(node)

        # Style mapping.
        if status == "purchased":
            row_style = "green"
            name_color = (160, 210, 160)
            desc_color = (120, 170, 120)
        elif status == "available":
            row_style = "dark"
            name_color = theme.TEXT_PRIMARY
            desc_color = theme.TEXT_MUTED
        elif status == "locked_doctrine":
            row_style = "dark"
            name_color = (160, 120, 60)
            desc_color = (130, 100, 50)
        else:  # locked_prereq / locked_gold
            row_style = "dark"
            name_color = (100, 100, 110)
            desc_color = (80, 80, 90)

        draw_selectable_row(screen=screen, rect=row_rect,
                            is_selected=is_selected, is_hovered=is_hovered, style=row_style)

        # Branch label chip (left edge).
        branch_chip_w = max(80, len(node.branch) * 8 + 16)
        StatusChip(
            rect=(row_rect.x + 8, row_rect.y + 8, branch_chip_w, 22),
            text=node.branch,
            style="info" if status == "available" else "default",
        ).draw(screen, self.small_font)

        # Name.
        name_x = row_rect.x + branch_chip_w + 20
        screen.blit(
            self.font.render(
                truncate_text(node.name, self.font, row_rect.width - branch_chip_w - 160),
                True, name_color,
            ),
            (name_x, row_rect.y + 6),
        )

        # Status chip (right edge).
        if status == "purchased":
            chip_text, chip_style = "Owned", "good"
        elif status == "available":
            chip_text, chip_style = f"{node.cost}g", "good"
        elif status == "locked_gold":
            chip_text, chip_style = f"{node.cost}g", "danger"
        elif status == "locked_doctrine":
            chip_text, chip_style = "Locked", "warning"
        else:
            chip_text, chip_style = "Locked", "default"

        StatusChip(
            rect=(row_rect.right - 96, row_rect.y + 8, 88, 26),
            text=chip_text,
            style=chip_style,
        ).draw(screen, self.small_font)

        # Description.
        screen.blit(
            self.small_font.render(
                truncate_text(node.description, self.small_font, row_rect.width - 120),
                True, desc_color,
            ),
            (row_rect.x + 12, row_rect.y + 38),
        )

    # ------------------------------------------------------------------
    # Status panel (right side)
    # ------------------------------------------------------------------

    def draw_status_panel(self, screen):
        from pygame_ui.widgets.card import Card

        Card(
            rect=self.status_rect,
            title="Guild Status",
            lines=[],
            fill_color=theme.PANEL_BG,
            border_color=theme.PANEL_BORDER,
            padding=18,
        ).draw(screen, self.title_font, self.font)

        upgrades      = self.state.guild_upgrades
        chosen        = getattr(upgrades, "doctrine", "")
        doctrine_text = upgrades.doctrine_label() if hasattr(upgrades, "doctrine_label") else "Undecided"
        x = self.status_rect[0] + 24
        y = self.status_rect[1] + 58

        SectionTitle("Capabilities", "Current guild infrastructure.").draw(
            screen=screen, title_font=self.font, subtitle_font=self.small_font, x=x, y=y)
        y += 48

        KeyValueGrid(
            rows=[
                ("Doctrine",    doctrine_text),
                ("Roster",      f"{len(self.state.roster)}/{upgrades.roster_capacity}"),
                ("Classes",     ", ".join(upgrades.unlocked_classes)),
                ("Recruit Cap", f"Lv {upgrades.recruit_level_cap}"),
                ("Market",      "Unlocked" if upgrades.market_unlocked else "Locked"),
                ("Rarity Cap",  upgrades.market_rarity_cap),
                ("Mission Cap", f"Diff {upgrades.mission_difficulty_cap}"),
                ("Stipend",     f"{upgrades.crown_stipend}g"),
                ("Training",    f"Lv {upgrades.training_hall_level}"),
            ],
            columns=1, column_width=560, row_gap=10,
            label_color=theme.TEXT_MUTED, value_color=theme.TEXT_PRIMARY,
            label_bold=True, value_bold=False, font_size=22, line_spacing=2,
        ).draw(screen=screen, font=self.font, x=x, y=y)
        y += 240

        # Doctrine fork call-to-action if not chosen yet.
        if not chosen:
            y += 10
            SectionTitle(
                "Choose Your Doctrine",
                "One permanent identity choice. Each path unlocks deeper upgrades.",
            ).draw(screen=screen, title_font=self.font, subtitle_font=self.small_font, x=x, y=y)
            y += 50
            for label, desc in [
                ("Militant",  "Combat strength, endurance, armory."),
                ("Merchant",  "Wealth, market access, Crown ties."),
                ("Scholarly", "Hero development, XP, recruitment."),
            ]:
                screen.blit(self.font.render(f"• {label}", True, theme.TEXT_PRIMARY), (x, y))
                screen.blit(self.small_font.render(f"  {desc}", True, theme.TEXT_MUTED), (x + 14, y + 24))
                y += 50
        else:
            # Show doctrine-specific bonuses.
            y += 10
            SectionTitle(
                f"{doctrine_text} Doctrine Active",
                "Your guild's identity is set. Deeper upgrades are now available.",
            ).draw(screen=screen, title_font=self.font, subtitle_font=self.small_font, x=x, y=y)
            y += 50

            bonus_rows = []
            eq_bonus = int(getattr(upgrades, "equip_capacity_bonus", 0))
            inj_bonus = int(getattr(upgrades, "injury_recovery_bonus", 0))
            mkt_disc  = int(getattr(upgrades, "market_refresh_discount", 0))
            xp_bonus  = int(getattr(upgrades, "xp_bonus_percent", 0))

            if eq_bonus  > 0: bonus_rows.append(("Equip Capacity",     f"+{eq_bonus} slot(s)"))
            if inj_bonus > 0: bonus_rows.append(("Injury Recovery",    f"-{inj_bonus} yr(s)"))
            if mkt_disc  > 0: bonus_rows.append(("Market Refresh",     f"-{mkt_disc}g"))
            if xp_bonus  > 0: bonus_rows.append(("Mission XP Bonus",   f"+{xp_bonus}%"))

            if bonus_rows:
                KeyValueGrid(
                    rows=bonus_rows,
                    columns=1, column_width=560, row_gap=8,
                    label_color=theme.TEXT_MUTED, value_color=(180, 220, 180),
                    label_bold=True, value_bold=True, font_size=22, line_spacing=2,
                ).draw(screen=screen, font=self.font, x=x, y=y)
                y += len(bonus_rows) * 30 + 10

        # Selected upgrade detail block.
        if self.selected_upgrade_id:
            node = get_upgrade(self.selected_upgrade_id)
            if node:
                y += 16
                SectionTitle("Selected Upgrade", "").draw(
                    screen=screen, title_font=self.font, subtitle_font=self.small_font, x=x, y=y)
                y += 36
                detail_lines = [node.description]
                if node.drawback:
                    detail_lines.append(f"Drawback: {node.drawback}")
                if node.requires:
                    missing = [r for r in node.requires if not upgrades.has(r)]
                    if missing:
                        req_nodes = [get_upgrade(r) for r in missing]
                        req_names = [n.name if n else r for n, r in zip(req_nodes, missing)]
                        detail_lines.append(f"Needs: {', '.join(req_names)}")
                if node.doctrine_locks and not upgrades.doctrine_locked():
                    detail_lines.append(f"WARNING: locks to {node.doctrine_locks.title()} permanently.")

                TextBlock(
                    lines=detail_lines,
                    color=theme.TEXT_SECONDARY,
                    row_spacing=22,
                    max_lines=6,
                ).draw(screen=screen, font=self.small_font, x=x, y=y,
                       max_width=self.status_rect[2] - 48)

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------

    def build_buttons(self):
        buttons = [hub_button(self.on_return_to_hub, text="Hub")]

        if self.selected_upgrade_id:
            status = self._node_status_by_id(self.selected_upgrade_id)
            if status == "available":
                buttons.append(action_button(
                    "Buy Upgrade", self.buy_selected_upgrade, rect=(1660, 958, 180, 44)
                ))

        return buttons

    # ------------------------------------------------------------------
    # Interactions
    # ------------------------------------------------------------------

    def _handle_row_click(self, pos):
        node = self.upgrades_panel.item_at_pos(pos)
        if node is None:
            return
        status = self._node_status(node)
        if status == "purchased":
            self.status_message = f"{node.name} is already owned."
            self.selected_upgrade_id = None
            return
        self.selected_upgrade_id = node.id
        self.status_message = f"Selected: {node.name}"

    def buy_selected_upgrade(self):
        if self.selected_upgrade_id is None:
            self.status_message = "Select an upgrade first."
            return

        # Doctrine fork — warn and confirm via status message on first click,
        # then proceed on second click if same node is selected.
        node = get_upgrade(self.selected_upgrade_id)
        if node and node.doctrine_locks:
            if not getattr(self, "_doctrine_confirm_pending", False):
                self._doctrine_confirm_pending = True
                self.status_message = (
                    f"This will lock your guild to {node.doctrine_locks.title()} permanently. "
                    f"Click Buy Upgrade again to confirm."
                )
                return
            self._doctrine_confirm_pending = False

        result = buy_upgrade(self.state, self.selected_upgrade_id)
        self.status_message = result
        self.selected_upgrade_id = None
        self.sync_lists()

        if self.on_save_game:
            self.on_save_game()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _selected_node(self):
        if self.selected_upgrade_id is None:
            return None
        for node in self._visible_nodes():
            if node.id == self.selected_upgrade_id:
                return node
        return None

    def _node_status_by_id(self, upgrade_id):
        node = get_upgrade(upgrade_id)
        if node is None:
            return "locked_prereq"
        return self._node_status(node)