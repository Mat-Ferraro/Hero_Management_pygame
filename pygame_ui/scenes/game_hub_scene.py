import pygame

from ..widgets.button import Button
from ..widgets.panel import Panel


class GameHubScene:
    def __init__(
        self,
        state,
        on_open_guild,
        on_open_expedition,
        on_open_inventory,
        on_open_market,
        on_open_upgrades,
        on_save_game,
        on_return_to_menu,
        status_message="",
    ):
        self.state = state
        self.on_open_guild = on_open_guild
        self.on_open_expedition = on_open_expedition
        self.on_open_inventory = on_open_inventory
        self.on_open_market = on_open_market
        self.on_open_upgrades = on_open_upgrades
        self.on_save_game = on_save_game
        self.on_return_to_menu = on_return_to_menu
        self.status_message = status_message

        self.mouse_pos = (0, 0)

        self.header_font = pygame.font.SysFont(None, 30)
        self.font = pygame.font.SysFont(None, 24)
        self.button_font = pygame.font.SysFont(None, 28)

        self.header_panel = Panel((40, 40, 1200, 110), "Guild Hall")
        self.main_panel = Panel((40, 180, 1200, 480), "Choose Destination")

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for button in self.build_buttons():
                if button.rect.collidepoint(event.pos):
                    button.on_click()
                    return

    def update(self, mouse_pos):
        self.mouse_pos = mouse_pos

    def draw(self, screen):
        screen.fill((28, 28, 32))

        self.header_panel.draw(screen, self.header_font)
        self.main_panel.draw(screen, self.header_font)

        upgrades = self.state.guild_upgrades
        market_status = "Open" if upgrades.market_unlocked else "Locked"

        stats = (
            f"Gold: {self.state.gold}g    "
            f"Campaign Year: {self.state.year}    "
            f"Campaigns: {self.state.expedition - 1}    "
            f"Roster: {len(self.state.roster)}/{upgrades.roster_capacity}    "
            f"Classes: {', '.join(upgrades.unlocked_classes)}"
        )

        screen.blit(
            self.header_font.render(stats, True, (235, 235, 240)),
            (70, 92),
        )

        second_line = (
            f"Recruit Cap: Lv {upgrades.recruit_level_cap}    "
            f"Mission Cap: Diff {upgrades.mission_difficulty_cap}    "
            f"Market: {market_status}    "
            f"Crown Stipend: {upgrades.crown_stipend}g"
        )

        screen.blit(
            self.font.render(second_line, True, (190, 190, 205)),
            (70, 122),
        )

        if self.status_message:
            screen.blit(
                self.font.render(self.status_message, True, (180, 200, 230)),
                (560, 150),
            )

        for button in self.build_buttons():
            button.update(self.mouse_pos)
            button.draw(screen, self.button_font)

        self.draw_descriptions(screen)

    def draw_descriptions(self, screen):
        market_text = "Buy equipment using guild gold."
        if not self.state.guild_upgrades.market_unlocked:
            market_text = "Locked. Unlock this through Guild Upgrades."

        descriptions = [
            ("Guild", "Hire heroes, inspect roster, and manage satisfaction."),
            ("Expedition", "Prepare a party for a mission. Mission difficulty controls party size."),
            ("Inventory", "View items and equip heroes."),
            ("Market", market_text),
            ("Upgrades", "Expand roster capacity, recruit options, missions, and services."),
        ]

        y = 460
        for title, description in descriptions:
            text = f"{title}: {description}"
            screen.blit(self.font.render(text, True, (190, 190, 205)), (260, y))
            y += 28

    def build_buttons(self):
        return [
            Button((260, 250, 220, 56), "Guild", self.on_open_guild),
            Button((530, 250, 220, 56), "Expedition", self.on_open_expedition),
            Button((800, 250, 220, 56), "Inventory", self.on_open_inventory),
            Button((260, 330, 220, 56), "Market", self.on_open_market),
            Button((530, 330, 220, 56), "Upgrades", self.on_open_upgrades),
            Button((800, 330, 220, 56), "Save Game", self.on_save_game),
            Button((530, 405, 220, 48), "Main Menu", self.on_return_to_menu),
        ]