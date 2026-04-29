import pygame

from pygame_ui import theme
from pygame_ui.ui_helpers import wrap_text
from pygame_ui.widgets.panel import Panel


class DetailsPanel:
    def __init__(
        self,
        rect,
        title="",
        padding=24,
        title_height=44,
        row_spacing=20,
    ):
        self.panel = Panel(rect, title)
        self.padding = padding
        self.title_height = title_height
        self.row_spacing = row_spacing

    @property
    def rect(self):
        return self.panel.rect

    def draw_empty(self, screen, title_font, font, message):
        self.panel.draw(screen, title_font)
        screen.blit(
            font.render(message, True, theme.TEXT_MUTED),
            (self.rect.x + self.padding, self.rect.y + self.title_height + 4),
        )

    def draw_lines(self, screen, title_font, font, lines, max_width=None):
        self.panel.draw(screen, title_font)

        x = self.rect.x + self.padding
        y = self.rect.y + self.title_height
        width = max_width or (self.rect.width - self.padding * 2)

        for line in lines:
            for wrapped in wrap_text(line, font, width):
                screen.blit(font.render(wrapped, True, theme.TEXT_SECONDARY), (x, y))
                y += self.row_spacing

    def draw_two_columns(
        self,
        screen,
        title_font,
        font,
        left_lines,
        right_lines,
        left_width=540,
        right_width=540,
    ):
        self.panel.draw(screen, title_font)

        left_x = self.rect.x + self.padding
        right_x = self.rect.x + self.rect.width // 2
        start_y = self.rect.y + self.title_height

        y = start_y
        for line in left_lines:
            for wrapped in wrap_text(line, font, left_width):
                screen.blit(font.render(wrapped, True, theme.TEXT_SECONDARY), (left_x, y))
                y += self.row_spacing

        y = start_y
        for line in right_lines:
            for wrapped in wrap_text(line, font, right_width):
                screen.blit(font.render(wrapped, True, theme.TEXT_SECONDARY), (right_x, y))
                y += self.row_spacing