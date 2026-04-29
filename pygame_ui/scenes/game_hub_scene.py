import pygame

from ..widgets.button import Button
from ..widgets.panel import Panel


class GameHubScene:
    def __init__(
        self,
        state,
        on_open_guild,
        on_open_expedition,
        on_save_game,
        on_return_to_menu,
        status_message="",
    ):
        self.state = state
        self.on_open_guild = on_open_guild
        self.on_open_expedition = on_open_expedition
        self.on_save_game = on_save_game
        self.on_return_to_menu = on_return_to_menu
        self.status_message = status_message

        self.mouse_pos = (0, 0)

        self.title_font = pygame.font.SysFont(None, 56)
        self.header_font = pygame.font.SysFont(None, 30)
        self.font = pygame.font.SysFont(None, 24)
        self.button_font = pygame.font.SysFont(None, 28)

        self.header_panel = Panel((40, 40, 1200, 110), "Game Hub")
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

        stats = (
            f"Gold: {self.state.gold}g    "
            f"Year: {self.state.year}    "
            f"Expedition: {self.state.expedition}    "
            f"Contracts: {len(self.state.available_contracts)}    "
            f"Roster: {len(self.state.roster)}"
        )

        screen.blit(
            self.header_font.render(stats, True, (235, 235, 240)),
            (70, 92),
        )

        if self.status_message:
            screen.blit(
                self.font.render(self.status_message, True, (180, 200, 230)),
                (70, 125),
            )

        for button in self.build_buttons():
            button.update(self.mouse_pos)
            button.draw(screen, self.button_font)

        self.draw_descriptions(screen)

    def draw_descriptions(self, screen):
        descriptions = [
            ("Guild", "Hire heroes, inspect roster, and manage contracts."),
            ("Expedition", "Prepare a party and choose a dungeon."),
            ("Market", "Buy supplies and equipment. Coming soon."),
            ("Inventory", "View and equip items. Coming soon."),
        ]

        y = 440
        for title, description in descriptions:
            text = f"{title}: {description}"
            screen.blit(self.font.render(text, True, (190, 190, 205)), (260, y))
            y += 30

    def build_buttons(self):
        return [
            Button((260, 260, 220, 56), "Guild", self.on_open_guild),
            Button((530, 260, 220, 56), "Expedition", self.on_open_expedition),
            Button((800, 260, 220, 56), "Market", self.coming_soon_market),
            Button((260, 340, 220, 56), "Inventory", self.coming_soon_inventory),
            Button((530, 340, 220, 56), "Save Game", self.on_save_game),
            Button((800, 340, 220, 56), "Main Menu", self.on_return_to_menu),
        ]

    def coming_soon_market(self):
        self.status_message = "Market screen coming soon."

    def coming_soon_inventory(self):
        self.status_message = "Inventory screen coming soon."