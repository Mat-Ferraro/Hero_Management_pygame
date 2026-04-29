import pygame

from pygame_ui import theme
from pygame_ui.widgets.text_block import TextBlock


class Card:
    def __init__(
        self,
        rect,
        title="",
        lines=None,
        fill_color=None,
        border_color=None,
        padding=14,
        border_radius=10,
    ):
        self.rect = pygame.Rect(rect)
        self.title = title
        self.lines = list(lines or [])
        self.fill_color = fill_color or theme.ROW_DARK
        self.border_color = border_color or theme.ROW_DARK_BORDER
        self.padding = padding
        self.border_radius = border_radius

    def set_lines(self, lines):
        self.lines = list(lines or [])

    def draw(self, screen, title_font, font):
        pygame.draw.rect(screen, self.fill_color, self.rect, border_radius=self.border_radius)
        pygame.draw.rect(screen, self.border_color, self.rect, 1, border_radius=self.border_radius)

        y = self.rect.y + self.padding

        if self.title:
            screen.blit(
                title_font.render(str(self.title), True, theme.TEXT_PRIMARY),
                (self.rect.x + self.padding, y),
            )
            y += title_font.get_height() + 6

        TextBlock(
            self.lines,
            color=theme.TEXT_SECONDARY,
            row_spacing=font.get_height() + 4,
        ).draw(
            screen=screen,
            font=font,
            x=self.rect.x + self.padding,
            y=y,
            max_width=self.rect.width - self.padding * 2,
        )