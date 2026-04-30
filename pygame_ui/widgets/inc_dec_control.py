import pygame

from pygame_ui import theme
from pygame_ui.widgets.button import Button


class IncDecControl:
    def __init__(self, rect, title, value_getter, on_decrease, on_increase):
        self.rect = pygame.Rect(rect)
        self.title = title
        self.value_getter = value_getter
        self.on_decrease = on_decrease
        self.on_increase = on_increase

        self.decrease_button = None
        self.increase_button = None
        self._rebuild_buttons()

    def _rebuild_buttons(self):
        button_size = 36
        button_y = self.rect.y + 18

        self.decrease_button = Button(
            (self.rect.x, button_y, button_size, button_size),
            "-",
            self.on_decrease,
        )
        self.increase_button = Button(
            (self.rect.right - button_size, button_y, button_size, button_size),
            "+",
            self.on_increase,
        )

    def set_rect(self, rect):
        self.rect = pygame.Rect(rect)
        self._rebuild_buttons()

    def get_buttons(self):
        return [self.decrease_button, self.increase_button]

    def draw(self, screen, title_font, value_font):
        title_surface = title_font.render(self.title, True, theme.TEXT_MUTED)
        title_x = self.rect.centerx - title_surface.get_width() // 2
        title_y = self.rect.y
        screen.blit(title_surface, (title_x, title_y))

        value_text = self.value_getter() if callable(self.value_getter) else str(self.value_getter)
        value_surface = value_font.render(str(value_text), True, theme.TEXT_PRIMARY)
        value_x = self.rect.centerx - value_surface.get_width() // 2
        value_y = self.rect.y + 24
        screen.blit(value_surface, (value_x, value_y))