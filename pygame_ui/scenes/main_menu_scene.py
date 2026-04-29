import pygame

from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.widgets.card import Card
from pygame_ui.widgets.section_title import SectionTitle
from pygame_ui.widgets.status_chip import StatusChip
from pygame_ui.widgets.text_block import TextBlock

from ..widgets.button import Button


class MainMenuScene(SceneBase):
    def __init__(self, on_start_new_game, on_load_game, on_quit):
        super().__init__()

        self.on_start_new_game = on_start_new_game
        self.on_load_game = on_load_game
        self.on_quit = on_quit

        self.title_font = pygame.font.SysFont(None, 88)
        self.subtitle_font = pygame.font.SysFont(None, 32)
        self.button_font = pygame.font.SysFont(None, 34)

        self.status_message = ""

    def handle_event(self, event):
        self.handle_buttons_click(event, self.build_buttons())

    def draw(self, screen):
        self.clear_screen(screen, theme.MAIN_MENU_BG)

        self.draw_title(screen)
        self.draw_left_panel(screen)
        self.draw_right_panel(screen)
        self.update_and_draw_buttons(screen, self.build_buttons(), self.button_font)

        if self.status_message:
            status = self.subtitle_font.render(self.status_message, True, theme.TEXT_WARNING)
            status_rect = status.get_rect(center=(960, 930))
            screen.blit(status, status_rect)

    def draw_title(self, screen):
        title = self.title_font.render("Hero Management", True, (245, 245, 250))
        title_rect = title.get_rect(center=(960, 110))
        screen.blit(title, title_rect)

        subtitle = self.subtitle_font.render(
            "Build a guild. Sign heroes. Risk lives for treasure.",
            True,
            theme.TEXT_MUTED,
        )
        subtitle_rect = subtitle.get_rect(center=(960, 170))
        screen.blit(subtitle, subtitle_rect)

    def draw_left_panel(self, screen):
        Card(
            rect=(140, 250, 760, 620),
            title="Start Playing",
            lines=[],
            fill_color=theme.PANEL_BG,
            border_color=theme.PANEL_BORDER,
            padding=22,
        ).draw(screen, self.title_font, self.font)

        SectionTitle(
            "Guild Strategy RPG",
            "Grow your organization through risk, recovery, and long-term planning.",
        ).draw(
            screen=screen,
            title_font=self.font,
            subtitle_font=self.small_font,
            x=176,
            y=352,
        )

        TextBlock(
            lines=[
                "Recruit heroes with different strengths, needs, and long-term value.",
                "Equip them, train them, and form parties for dangerous expeditions.",
                "Use treasure and crown support to grow your guild into a lasting institution.",
                "Death should matter. Recovery should matter. Growth should feel earned.",
            ],
            color=theme.TEXT_SECONDARY,
            row_spacing=30,
        ).draw(
            screen=screen,
            font=self.font,
            x=176,
            y=452,
            max_width=680,
        )

        StatusChip((176, 700, 140, 30), "Management", "info").draw(screen, self.small_font)
        StatusChip((328, 700, 140, 30), "Tycoon", "info").draw(screen, self.small_font)
        StatusChip((480, 700, 140, 30), "Strategy", "warning").draw(screen, self.small_font)
        StatusChip((632, 700, 140, 30), "Permadeath", "danger").draw(screen, self.small_font)

    def draw_right_panel(self, screen):
        Card(
            rect=(1020, 250, 760, 620),
            title="Session Actions",
            lines=[],
            fill_color=theme.PANEL_BG,
            border_color=theme.PANEL_BORDER,
            padding=22,
        ).draw(screen, self.title_font, self.font)

        SectionTitle(
            "Choose an option",
            "Start fresh, continue a saved run, or exit.",
        ).draw(
            screen=screen,
            title_font=self.font,
            subtitle_font=self.small_font,
            x=1056,
            y=352,
        )

        TextBlock(
            lines=[
                "New Game begins a fresh guild from the opening state.",
                "Load Game continues from your most recent save file.",
                "Quit closes the application.",
            ],
            color=theme.TEXT_SECONDARY,
            row_spacing=30,
        ).draw(
            screen=screen,
            font=self.font,
            x=1056,
            y=452,
            max_width=680,
        )

    def build_buttons(self):
        return [
            Button(
                (1240, 560, 320, 58),
                "Start New Game",
                self.on_start_new_game,
            ),
            Button(
                (1240, 640, 320, 58),
                "Load Game",
                self.on_load_game,
            ),
            Button(
                (1240, 720, 320, 58),
                "Quit",
                self.on_quit,
            ),
        ]