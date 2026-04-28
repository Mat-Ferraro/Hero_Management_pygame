import pygame

from ..widgets.button import Button


class MainMenuScene:
    def __init__(self, on_start_new_game, on_load_game, on_quit):
        self.on_start_new_game = on_start_new_game
        self.on_load_game = on_load_game
        self.on_quit = on_quit

        self.title_font = pygame.font.SysFont(None, 72)
        self.subtitle_font = pygame.font.SysFont(None, 28)
        self.button_font = pygame.font.SysFont(None, 30)

        self.mouse_pos = (0, 0)
        self.status_message = ""

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for button in self.build_buttons():
                if button.rect.collidepoint(event.pos):
                    button.on_click()
                    return

    def update(self, mouse_pos):
        self.mouse_pos = mouse_pos

    def draw(self, screen):
        screen.fill((24, 24, 30))

        title = self.title_font.render("Hero Management", True, (245, 245, 250))
        title_rect = title.get_rect(center=(640, 170))
        screen.blit(title, title_rect)

        subtitle = self.subtitle_font.render(
            "Build a guild. Sign heroes. Risk lives for treasure.",
            True,
            (180, 180, 195),
        )
        subtitle_rect = subtitle.get_rect(center=(640, 230))
        screen.blit(subtitle, subtitle_rect)

        for button in self.build_buttons():
            button.update(self.mouse_pos)
            button.draw(screen, self.button_font)

        if self.status_message:
            status = self.subtitle_font.render(self.status_message, True, (210, 180, 180))
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