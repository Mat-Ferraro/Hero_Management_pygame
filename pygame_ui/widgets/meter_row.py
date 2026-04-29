import pygame

from pygame_ui import theme
from pygame_ui.widgets.progress_bar import ProgressBar


class MeterRow:
    def __init__(
        self,
        label,
        value,
        maximum,
        value_text=None,
        fill_color=(100, 170, 120),
    ):
        self.label = label
        self.value = value
        self.maximum = maximum
        self.value_text = value_text
        self.fill_color = fill_color

    def draw(self, screen, font, x, y, width=420, label_width=120, bar_height=16):
        label_surface = font.render(str(self.label), True, theme.TEXT_MUTED)
        screen.blit(label_surface, (x, y))

        bar_x = x + label_width
        bar_rect = pygame.Rect(bar_x, y + 3, width - label_width, bar_height)

        text = self.value_text
        if text is None:
            text = f"{self.value}/{self.maximum}"

        ProgressBar(
            rect=bar_rect,
            value=self.value,
            maximum=self.maximum,
            label=text,
            fill_color=self.fill_color,
        ).draw(screen, font)

        return y + max(label_surface.get_height(), bar_height) + 8