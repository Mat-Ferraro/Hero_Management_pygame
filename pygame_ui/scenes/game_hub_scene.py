from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.widgets.card import Card
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.navigation_buttons import main_menu_button
from pygame_ui.widgets.resource_header import ResourceHeader
from pygame_ui.widgets.section_title import SectionTitle
from pygame_ui.widgets.state_overlay import StateOverlay
from pygame_ui.widgets.status_chip import StatusChip
from pygame_ui.widgets.text_block import TextBlock

from ..widgets.button import Button


class GameHubScene(SceneBase):
    def __init__(
        self,
        state,
        on_open_guild,
        on_open_expedition,
        on_open_inventory,
        on_open_market,
        on_open_training,
        on_open_upgrades,
        on_save_game,
        on_return_to_menu,
        status_message="",
    ):
        super().__init__()

        self.state = state
        self.on_open_guild = on_open_guild
        self.on_open_expedition = on_open_expedition
        self.on_open_inventory = on_open_inventory
        self.on_open_market = on_open_market
        self.on_open_training = on_open_training
        self.on_open_upgrades = on_open_upgrades
        self.on_save_game = on_save_game
        self.on_return_to_menu = on_return_to_menu
        self.status_message = status_message

        self.button_font = self.title_font
        self.overlay = StateOverlay()

    def handle_event(self, event):
        if self.overlay.visible:
            return

        self.handle_buttons_click(event, self.build_buttons())

    def draw(self, screen):
        self.clear_screen(screen)

        self.draw_header(screen)
        self.draw_main_cards(screen)
        self.draw_footer_summary(screen)
        self.update_and_draw_buttons(screen, self.build_buttons(), self.button_font)
        self.overlay.draw(screen, self.title_font, self.font)

    def draw_header(self, screen):
        upgrades = self.state.guild_upgrades

        HeaderPanel(
            rect=(40, 30, 1840, 110),
            title="Guild Hall",
            stats="",
            status_message=self.status_message,
            stats_pos=(70, 82),
            status_pos=(980, 122),
        ).draw(screen, self.title_font, self.header_font, self.font)

        ResourceHeader(
            resources=[
                ("Gold", f"{self.state.gold}g"),
                ("Year", self.state.year),
                ("Runs", self.state.expedition - 1),
                ("Roster", f"{len(self.state.roster)}/{upgrades.roster_capacity}"),
                ("Classes", ", ".join(upgrades.unlocked_classes)),
            ],
            spacing=185,
        ).draw(screen, self.font, 60, 82)

        second_line = (
            f"Recruit Cap Lv {upgrades.recruit_level_cap}    "
            f"Mission Cap Diff {upgrades.mission_difficulty_cap}    "
            f"Training Hall Lv {upgrades.training_hall_level}    "
            f"Crown Stipend {upgrades.crown_stipend}g"
        )
        screen.blit(
            self.font.render(second_line, True, theme.TEXT_MUTED),
            (60, 112),
        )

    def draw_main_cards(self, screen):
        self.draw_management_card(screen)
        self.draw_progression_card(screen)
        self.draw_operations_card(screen)

    def draw_management_card(self, screen):
        rect = (40, 180, 560, 500)
        Card(
            rect=rect,
            title="Guild Management",
            lines=[],
            fill_color=theme.PANEL_BG,
            border_color=theme.PANEL_BORDER,
            padding=18,
        ).draw(screen, self.title_font, self.font)

        SectionTitle(
            "Roster & Contracts",
            "Hire, inspect, equip, and train your heroes.",
        ).draw(screen, self.font, self.small_font, 66, 230)

        TextBlock(
            lines=[
                "Guild: Hire recruits, inspect heroes, and release underperformers.",
                "Inventory: Equip items and review hero loadouts.",
                "Training: Spend gold for safe XP gains.",
            ],
            color=theme.TEXT_SECONDARY,
            row_spacing=26,
        ).draw(
            screen=screen,
            font=self.font,
            x=66,
            y=290,
            max_width=500,
        )

        StatusChip((66, 420, 120, 28), "Roster", "info").draw(screen, self.small_font)
        StatusChip((196, 420, 120, 28), "Inventory", "info").draw(screen, self.small_font)
        StatusChip(
            (326, 420, 120, 28),
            f"Training Lv {self.state.guild_upgrades.training_hall_level}",
            "good" if self.state.guild_upgrades.training_hall_level > 0 else "locked",
        ).draw(screen, self.small_font)

    def draw_progression_card(self, screen):
        rect = (660, 180, 560, 500)
        Card(
            rect=rect,
            title="Guild Growth",
            lines=[],
            fill_color=theme.PANEL_BG,
            border_color=theme.PANEL_BORDER,
            padding=18,
        ).draw(screen, self.title_font, self.font)

        SectionTitle(
            "Tycoon Layer",
            "Invest gold to expand your guild’s capabilities.",
        ).draw(screen, self.font, self.small_font, 686, 230)

        TextBlock(
            lines=[
                "Upgrades unlock classes, improve roster size, raise recruit level caps, and expand mission access.",
                "Market availability and training access are also driven by guild upgrades.",
            ],
            color=theme.TEXT_SECONDARY,
            row_spacing=26,
        ).draw(
            screen=screen,
            font=self.font,
            x=686,
            y=290,
            max_width=500,
        )

        upgrades = self.state.guild_upgrades
        StatusChip((686, 420, 120, 28), "Upgrades", "info").draw(screen, self.small_font)
        StatusChip(
            (816, 420, 140, 28),
            "Market Open" if upgrades.market_unlocked else "Market Locked",
            "good" if upgrades.market_unlocked else "locked",
        ).draw(screen, self.small_font)
        StatusChip(
            (966, 420, 180, 28),
            f"Mission Diff {upgrades.mission_difficulty_cap}",
            "warning" if upgrades.mission_difficulty_cap >= 3 else "info",
        ).draw(screen, self.small_font)

    def draw_operations_card(self, screen):
        rect = (1280, 180, 600, 500)
        Card(
            rect=rect,
            title="Operations",
            lines=[],
            fill_color=theme.PANEL_BG,
            border_color=theme.PANEL_BORDER,
            padding=18,
        ).draw(screen, self.title_font, self.font)

        SectionTitle(
            "Deploy Heroes",
            "Build a party, choose a mission, and send them out.",
        ).draw(screen, self.font, self.small_font, 1306, 230)

        TextBlock(
            lines=[
                "Expeditions are the primary source of gold, XP, and risk.",
                "Stronger missions require larger parties and better preparation.",
                "Deaths and injuries can permanently affect your guild’s future.",
            ],
            color=theme.TEXT_SECONDARY,
            row_spacing=26,
        ).draw(
            screen=screen,
            font=self.font,
            x=1306,
            y=290,
            max_width=540,
        )

        StatusChip((1306, 430, 140, 28), "Expeditions", "warning").draw(screen, self.small_font)
        StatusChip((1456, 430, 120, 28), "Campaign", "info").draw(screen, self.small_font)
        StatusChip((1586, 430, 120, 28), "Menu", "default").draw(screen, self.small_font)

    def draw_footer_summary(self, screen):
        footer_rect = (40, 720, 1840, 300)
        Card(
            rect=footer_rect,
            title="Current Guild Snapshot",
            lines=[],
            fill_color=theme.PANEL_BG,
            border_color=theme.PANEL_BORDER,
            padding=18,
        ).draw(screen, self.title_font, self.font)

        upgrades = self.state.guild_upgrades

        left_lines = [
            f"Gold Available: {self.state.gold}g",
            f"Roster: {len(self.state.roster)}/{upgrades.roster_capacity}",
            f"Available Recruits: {len(self.state.available_contracts)}",
            f"Inventory Items: {len(self.state.inventory)}",
        ]

        middle_lines = [
            f"Unlocked Classes: {', '.join(upgrades.unlocked_classes)}",
            f"Training Hall Level: {upgrades.training_hall_level}",
            f"Market: {'Unlocked' if upgrades.market_unlocked else 'Locked'}",
            f"Crown Stipend: {upgrades.crown_stipend}g",
        ]

        right_lines = [
            f"Campaign Year: {self.state.year}",
            f"Completed Expeditions: {self.state.expedition - 1}",
            f"Mission Difficulty Cap: {upgrades.mission_difficulty_cap}",
            f"Recruit Level Cap: {upgrades.recruit_level_cap}",
        ]

        TextBlock(left_lines, color=theme.TEXT_SECONDARY, row_spacing=26).draw(
            screen, self.font, 66, 778, 480
        )
        TextBlock(middle_lines, color=theme.TEXT_SECONDARY, row_spacing=26).draw(
            screen, self.font, 690, 778, 480
        )
        TextBlock(right_lines, color=theme.TEXT_SECONDARY, row_spacing=26).draw(
            screen, self.font, 1310, 778, 480
        )

    def build_buttons(self):
        return [
            Button((90, 520, 220, 56), "Guild", self.on_open_guild),
            Button((330, 520, 220, 56), "Inventory", self.on_open_inventory),

            Button((690, 500, 220, 56), "Market", self.on_open_market),
            Button((930, 500, 220, 56), "Upgrades", self.on_open_upgrades),
            Button((810, 570, 220, 56), "Training", self.on_open_training),

            Button((1330, 520, 220, 56), "Expedition", self.on_open_expedition),

            main_menu_button(self.on_return_to_menu, rect=(1650, 930, 180, 52)),
        ]