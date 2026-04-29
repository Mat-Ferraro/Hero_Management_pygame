import pygame

from pygame_ui import theme


class ToastMessage:
    def __init__(self, duration=2.5):
        self.text = ""
        self.duration = duration
        self.remaining = 0.0

    def show(self, text, duration=None):
        self.text = text
        self.remaining = duration if duration is not None else self.duration

    def update(self, dt):
        if self.remaining > 0:
            self.remaining = max(0.0, self.remaining - dt)

    def is_visible(self):
        return self.remaining > 0 and bool(self.text)

    def draw(self, screen, font):
        if not self.is_visible():
            return

        padding_x = 18
        padding_y = 10

        text_surface = font.render(self.text, True, theme.TEXT_PRIMARY)
        rect = text_surface.get_rect()
        rect.width += padding_x * 2
        rect.height += padding_y * 2
        rect.centerx = screen.get_width() // 2
        rect.bottom = screen.get_height() - 24

        pygame.draw.rect(screen, (40, 40, 50), rect, border_radius=8)
        pygame.draw.rect(screen, theme.PANEL_BORDER, rect, 1, border_radius=8)

        screen.blit(
            text_surface,
            (rect.x + padding_x, rect.y + padding_y),
        )