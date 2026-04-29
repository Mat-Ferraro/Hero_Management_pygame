import pygame

from pygame_ui import theme


class ProgressBar:
    def __init__(
        self,
        rect,
        value=0,
        maximum=100,
        label="",
        fill_color=(100, 170, 120),
        background_color=(35, 35, 42),
        border_color=theme.PANEL_BORDER,
    ):
        self.rect = pygame.Rect(rect)
        self.value = value
        self.maximum = max(1, maximum)
        self.label = label
        self.fill_color = fill_color
        self.background_color = background_color
        self.border_color = border_color

    def set_value(self, value, maximum=None, label=None):
        self.value = value

        if maximum is not None:
            self.maximum = max(1, maximum)

        if label is not None:
            self.label = label

    def percent(self):
        return max(0.0, min(1.0, self.value / self.maximum))

    def draw(self, screen, font=None):
        pygame.draw.rect(screen, self.background_color, self.rect, border_radius=6)

        fill_width = int(self.rect.width * self.percent())
        if fill_width > 0:
            fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
            pygame.draw.rect(screen, self.fill_color, fill_rect, border_radius=6)

        pygame.draw.rect(screen, self.border_color, self.rect, 1, border_radius=6)

        if font and self.label:
            text_surface = font.render(str(self.label), True, theme.TEXT_PRIMARY)
            text_rect = text_surface.get_rect(center=self.rect.center)
            screen.blit(text_surface, text_rect)