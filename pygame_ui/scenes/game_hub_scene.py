"""
pygame_ui/scenes/game_hub_scene.py

Guild hub — the main management screen between campaigns.

Equipment / reputation additions:
  - Guild card now shows total equipped items and items in inventory.
  - Reputation standing shown in the Campaign card and summary panel.
  - Doctrine label shown in Operations card if one has been chosen.
"""

from core.game_state import campaign_is_active
from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.widgets.card import Card
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.label_value_text import LabelValueText
from pygame_ui.widgets.navigation_buttons import main_menu_button
from pygame_ui.widgets.resource_header import ResourceHeader
from pygame_ui.widgets.section_title import SectionTitle
from pygame_ui.widgets.text_block import TextBlock

from ..widgets.button import Button


class GameHubScene(SceneBase):
    def __init__(
        self,
        state,
        on_open_guild,
        on_open_campaign,
        on_open_inventory,
        on_open_market,
        on_open_training,
        on_open_upgrades,
        on_open_rivals,
        on_open_legacy,
        on_save_game,
        on_return_to_menu,
        status_message="",
    ):
        super().__init__()

        self.state = state
        self.on_open_guild = on_open_guild
        self.on_open_campaign = on_open_campaign
        self.on_open_inventory = on_open_inventory
        self.on_open_market = on_open_market
        self.on_open_training = on_open_training
        self.on_open_upgrades = on_open_upgrades
        self.on_open_rivals = on_open_rivals
        self.on_open_legacy = on_open_legacy
        self.on_save_game = on_save_game
        self.on_return_to_menu = on_return_to_menu

        self.status_message = status_message or "Manage your guild and prepare for the next campaign."

        self.hero_card_rect       = (60,   150, 540, 320)
        self.operations_card_rect = (690,  150, 540, 320)
        self.world_card_rect      = (1320, 150, 540, 320)
        self.summary_card_rect    = (60,   720, 1800, 250)

    def handle_event(self, event):
        if self.handle_buttons_click(event, self.build_buttons()):
            return

    def update(self, mouse_pos):
        super().update(mouse_pos)

    def draw(self, screen):
        self.clear_screen(screen)
        self.draw_header(screen)
        self.draw_cards(screen)
        self.draw_summary(screen)
        self.update_and_draw_buttons(screen, self.build_buttons())

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def draw_header(self, screen):
        reputation = getattr(self.state, "reputation", None)
        standing_label = reputation.label() if reputation else "Neutral"

        HeaderPanel(
            rect=(40, 30, 1840, 96),
            title="Guild Hub",
            stats="",
            status_message=self.status_message,
            stats_pos=(60, 74),
            status_pos=(980, 110),
        ).draw(screen, self.title_font, self.header_font, self.font)

        ResourceHeader(
            resources=[
                ("Gold",      f"{self.state.gold}g"),
                ("Year",      self.state.year),
                ("Roster",    f"{len(self.state.roster)}/{self.state.guild_upgrades.roster_capacity}"),
                ("Recruits",  len(self.state.available_contracts)),
                ("Standing",  standing_label),
            ],
            spacing=200,
            item_max_width=190,
            font_size=24,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=False,
            value_bold=True,
        ).draw(screen, self.font, 60, 72)

    # ------------------------------------------------------------------
    # Cards
    # ------------------------------------------------------------------

    def draw_cards(self, screen):
        self.draw_guild_card(screen)
        self.draw_operations_card(screen)
        self.draw_world_card(screen)

    def draw_guild_card(self, screen):
        Card(self.hero_card_rect, title="Guild").draw(screen, self.title_font, self.font)

        x = self.hero_card_rect[0] + 24
        y = self.hero_card_rect[1] + 58
        w = self.hero_card_rect[2] - 48

        y = SectionTitle("Roster Overview").draw(screen, self.font, self.small_font, x, y)
        y += 8

        roster_count    = len(self.state.roster)
        injured_count   = sum(1 for h in self.state.roster if getattr(h, "injured_years_remaining", 0) > 0)
        unhappy_count   = sum(1 for h in self.state.roster if getattr(h, "satisfaction", 100) < 50)
        equipped_count  = sum(len(h.equipment) for h in self.state.roster)
        inventory_count = len(self.state.inventory)
        retired_count   = len(getattr(self.state, "retired_heroes", []))

        # Legacy summary.
        try:
            from systems.guild.retirement_legacy import compute_legacy
            legacy = compute_legacy(self.state)
            legacy_line = f"Legacy Bonuses: +{legacy.total_gold_stipend_bonus}g" if legacy.has_any_legacy() else "Legacy: None yet"
        except Exception:
            legacy_line = ""

        lines = [
            f"Active Heroes: {roster_count}",
            f"Injured: {injured_count}",
            f"Low Satisfaction: {unhappy_count}",
            f"Items Equipped: {equipped_count}",
            f"Inventory Items: {inventory_count}",
            f"Retired Heroes: {retired_count}",
        ]
        if legacy_line:
            lines.append(legacy_line)

        TextBlock(
            lines=lines,
            color=theme.TEXT_SECONDARY,
            row_spacing=22,
            max_lines=8,
        ).draw(screen, self.font, x, y, w)

    def draw_operations_card(self, screen):
        Card(self.operations_card_rect, title="Operations").draw(screen, self.title_font, self.font)

        x = self.operations_card_rect[0] + 24
        y = self.operations_card_rect[1] + 58
        w = self.operations_card_rect[2] - 48

        y = SectionTitle("Guild Facilities").draw(screen, self.font, self.small_font, x, y)
        y += 8

        upgrades = self.state.guild_upgrades
        doctrine_text = upgrades.doctrine_label() if hasattr(upgrades, "doctrine_label") else "Undecided"

        TextBlock(
            lines=[
                f"Doctrine: {doctrine_text}",
                f"Training Hall: Level {upgrades.training_hall_level}",
                f"Market: {'Unlocked' if upgrades.market_unlocked else 'Locked'}",
                f"Mission Cap: Difficulty {upgrades.mission_difficulty_cap}",
                f"Crown Stipend: {upgrades.crown_stipend}g",
            ],
            color=theme.TEXT_SECONDARY,
            row_spacing=22,
            max_lines=6,
        ).draw(screen, self.font, x, y, w)

    def draw_world_card(self, screen):
        Card(self.world_card_rect, title="Campaign").draw(screen, self.title_font, self.font)

        x = self.world_card_rect[0] + 24
        y = self.world_card_rect[1] + 58
        w = self.world_card_rect[2] - 48

        runtime         = getattr(self.state, "campaign_runtime", None)
        rival_count     = len(getattr(self.state, "rival_guilds", []))
        campaign_status = "Active" if campaign_is_active(self.state) else "Inactive"
        campaign_time   = f"{runtime.elapsed_time:.1f}" if runtime is not None else "0.0"

        reputation     = getattr(self.state, "reputation", None)
        standing_val   = getattr(reputation, "standing", 0) if reputation else 0
        standing_label = reputation.label() if reputation else "Neutral"
        standing_text  = f"{standing_label} ({standing_val:+d})"

        y = SectionTitle("World State").draw(screen, self.font, self.small_font, x, y)
        y += 8

        TextBlock(
            lines=[
                f"Guild Standing: {standing_text}",
                f"Campaign Runtime: {campaign_status}",
                f"Campaign Time: {campaign_time}",
                f"Tracked Rivals: {rival_count}",
                f"Expeditions Completed: {self.state.expedition - 1}",
            ],
            color=theme.TEXT_SECONDARY,
            row_spacing=22,
            max_lines=6,
        ).draw(screen, self.font, x, y, w)

    # ------------------------------------------------------------------
    # Summary panel
    # ------------------------------------------------------------------

    def draw_summary(self, screen):
        Card(self.summary_card_rect, title="Guild Summary").draw(screen, self.title_font, self.font)

        upgrades        = self.state.guild_upgrades
        rival_count     = len(getattr(self.state, "rival_guilds", []))
        campaign_runtime = getattr(self.state, "campaign_runtime", None)
        campaign_status  = "Active" if campaign_is_active(self.state) else "Inactive"
        campaign_time    = f"{campaign_runtime.elapsed_time:.1f}" if campaign_runtime is not None else "0.0"

        reputation      = getattr(self.state, "reputation", None)
        standing_label  = reputation.label() if reputation else "Neutral"
        standing_val    = getattr(reputation, "standing", 0) if reputation else 0
        equipped_count  = sum(len(h.equipment) for h in self.state.roster)
        doctrine_text   = upgrades.doctrine_label() if hasattr(upgrades, "doctrine_label") else "Undecided"

        left_pairs = [
            ("Gold Available",    f"{self.state.gold}g"),
            ("Roster",            f"{len(self.state.roster)}/{upgrades.roster_capacity}"),
            ("Available Recruits", len(self.state.available_contracts)),
            ("Items Equipped",    equipped_count),
            ("Inventory Items",   len(self.state.inventory)),
        ]

        middle_pairs = [
            ("Doctrine",          doctrine_text),
            ("Unlocked Classes",  ", ".join(upgrades.unlocked_classes)),
            ("Training Hall",     f"Level {upgrades.training_hall_level}"),
            ("Market",            "Unlocked" if upgrades.market_unlocked else "Locked"),
            ("Crown Stipend",     f"{upgrades.crown_stipend}g"),
        ]

        right_pairs = [
            ("Guild Standing",    f"{standing_label} ({standing_val:+d})"),
            ("Campaign Year",     self.state.year),
            ("Expeditions Done",  self.state.expedition - 1),
            ("Mission Cap",       f"Difficulty {upgrades.mission_difficulty_cap}"),
            ("Rival Guilds",      rival_count),
            ("Campaign",          campaign_status),
        ]

        self.draw_label_value_column(screen, left_pairs,   66,   778, 480)
        self.draw_label_value_column(screen, middle_pairs, 690,  778, 480)
        self.draw_label_value_column(screen, right_pairs,  1310, 778, 480)

    def draw_label_value_column(self, screen, pairs, x, y, max_width):
        current_y   = y
        row_spacing = 26

        for label, value in pairs:
            LabelValueText(
                label=label,
                value=value,
                label_color=theme.TEXT_PRIMARY,
                value_color=theme.TEXT_PRIMARY,
                label_bold=True,
                value_bold=False,
                font_size=24,
            ).draw(screen=screen, font=self.font, x=x, y=current_y, max_width=max_width)
            current_y += row_spacing

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------

    def build_buttons(self):
        campaign_label = "Campaign" if not campaign_is_active(self.state) else "Resume Campaign"

        return [
            Button((90,   520, 220, 56), "Guild",          self.on_open_guild),
            Button((330,  520, 220, 56), "Inventory",      self.on_open_inventory),
            Button((690,  500, 220, 56), "Market",         self.on_open_market),
            Button((930,  500, 220, 56), "Upgrades",       self.on_open_upgrades),
            Button((810,  570, 220, 56), "Training",       self.on_open_training),
            Button((1350, 500, 220, 56), campaign_label,   self.on_open_campaign),
            Button((1350, 570, 220, 56), "Rivals",         self.on_open_rivals),
            Button((570,  570, 220, 56), "Legacy",         self.on_open_legacy),
            Button((1650,  72, 140, 36), "Save",           self.on_save_game),
            main_menu_button(self.on_return_to_menu, rect=(1650, 930, 180, 52)),
        ]