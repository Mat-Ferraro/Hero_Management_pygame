from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.panel import Panel

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
        self.main_panel = Panel((40, 180, 1200, 500), "Choose Destination")

    def handle_event(self, event):
        self.handle_buttons_click(event, self.build_buttons())

    def draw(self, screen):
        self.clear_screen(screen)
        self.draw_header(screen)

        self.main_panel.draw(screen, self.title_font)
        self.draw_descriptions(screen)
        self.update_and_draw_buttons(screen, self.build_buttons(), self.button_font)

    def draw_header(self, screen):
        upgrades = self.state.guild_upgrades
        market_status = "Open" if upgrades.market_unlocked else "Locked"
        training_status = f"Lv {upgrades.training_hall_level}" if upgrades.training_hall_level > 0 else "Locked"

        stats = (
            f"Gold: {self.state.gold}g    "
            f"Campaign Year: {self.state.year}    "
            f"Campaigns: {self.state.expedition - 1}    "
            f"Roster: {len(self.state.roster)}/{upgrades.roster_capacity}    "
            f"Classes: {', '.join(upgrades.unlocked_classes)}"
        )

        HeaderPanel(
            rect=(40, 40, 1200, 110),
            title="Guild Hall",
            stats=stats,
            status_message=self.status_message,
            stats_pos=(70, 92),
            status_pos=(560, 150),
        ).draw(screen, self.title_font, self.header_font, self.font)

        second_line = (
            f"Recruit Cap: Lv {upgrades.recruit_level_cap}    "
            f"Mission Cap: Diff {upgrades.mission_difficulty_cap}    "
            f"Market: {market_status}    "
            f"Training Hall: {training_status}    "
            f"Stipend: {upgrades.crown_stipend}g"
        )

        screen.blit(
            self.font.render(second_line, True, theme.TEXT_MUTED),
            (70, 122),
        )

    def draw_descriptions(self, screen):
        market_text = "Buy equipment using guild gold."
        if not self.state.guild_upgrades.market_unlocked:
            market_text = "Locked. Unlock this through Guild Upgrades."

        training_text = "Train heroes safely for gold."
        if self.state.guild_upgrades.training_hall_level <= 0:
            training_text = "Locked. Build the Training Hall through Guild Upgrades."

        descriptions = [
            ("Guild", "Hire heroes, inspect roster, and manage satisfaction."),
            ("Expedition", "Prepare a party for a mission. Mission difficulty controls party size."),
            ("Inventory", "View items and equip heroes."),
            ("Market", market_text),
            ("Training", training_text),
            ("Upgrades", "Expand roster capacity, recruit options, missions, and services."),
        ]

        y = 475
        for title, description in descriptions:
            text = f"{title}: {description}"
            screen.blit(self.font.render(text, True, theme.TEXT_MUTED), (260, y))
            y += 28

    def build_buttons(self):
        return [
            Button((230, 245, 200, 52), "Guild", self.on_open_guild),
            Button((470, 245, 200, 52), "Expedition", self.on_open_expedition),
            Button((710, 245, 200, 52), "Inventory", self.on_open_inventory),
            Button((950, 245, 200, 52), "Market", self.on_open_market),
            Button((230, 325, 200, 52), "Training", self.on_open_training),
            Button((470, 325, 200, 52), "Upgrades", self.on_open_upgrades),
            Button((710, 325, 200, 52), "Save Game", self.on_save_game),
            Button((950, 325, 200, 52), "Main Menu", self.on_return_to_menu),
        ]