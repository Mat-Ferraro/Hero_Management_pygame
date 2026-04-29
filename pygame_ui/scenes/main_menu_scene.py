import pygame

from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase

from ..widgets.button import Button


class MainMenuScene(SceneBase):
    def __init__(self, on_start_new_game, on_load_game, on_quit):
        super().__init__()

        self.on_start_new_game = on_start_new_game
        self.on_load_game = on_load_game
        self.on_quit = on_quit

        self.title_font = pygame.font.SysFont(None, 72)
        self.subtitle_font = pygame.font.SysFont(None, 28)
        self.button_font = pygame.font.SysFont(None, 30)

        self.status_message = ""

    def handle_event(self, event):
        self.handle_buttons_click(event, self.build_buttons())

    def draw(self, screen):
        self.clear_screen(screen, theme.MAIN_MENU_BG)

        title = self.title_font.render("Hero Management", True, (245, 245, 250))
        title_rect = title.get_rect(center=(640, 170))
        screen.blit(title, title_rect)

        subtitle = self.subtitle_font.render(
            "Build a guild. Sign heroes. Risk lives for treasure.",
            True,
            theme.TEXT_MUTED,
        )
        subtitle_rect = subtitle.get_rect(center=(640, 230))
        screen.blit(subtitle, subtitle_rect)

        self.update_and_draw_buttons(screen, self.build_buttons(), self.button_font)

        if self.status_message:
            status = self.subtitle_font.render(self.status_message, True, theme.TEXT_WARNING)
            status_rect = status.get_rect(center=(640, 520))
            screen.blit(status, status_rect)

    def build_buttons(self):
        return [
            Button(
                (510, 300, 260, 48),
                "Start New Game",
                self.on_start_new_game,
            ),
            Button(
                (510, 365, 260, 48),
                "Load Game",
                self.on_load_game,
            ),
            Button(
                (510, 430, 260, 48),
                "Quit",
                self.on_quit,
            ),
        ]