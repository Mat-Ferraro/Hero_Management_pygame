import pygame

from pygame_ui import theme
from pygame_ui.widgets.text_block import TextBlock


class Tooltip:
    def __init__(
        self,
        text="",
        max_width=320,
        padding=12,
        offset=(18, 18),
    ):
        self.text = text
        self.max_width = max_width
        self.padding = padding
        self.offset = offset
        self.visible = False

    def show(self, text):
        self.text = text
        self.visible = True

    def hide(self):
        self.visible = False

    def draw(self, screen, font, mouse_pos):
        if not self.visible or not self.text:
            return

        x = mouse_pos[0] + self.offset[0]
        y = mouse_pos[1] + self.offset[1]

        wrapped = []
        for line in str(self.text).splitlines():
            wrapped.extend(TextBlock([line]).lines)

        # Calculate wrapped text using existing helper through TextBlock draw behavior.
        from pygame_ui.ui_helpers import wrap_text

        lines = []
        for line in str(self.text).splitlines():
            lines.extend(wrap_text(line, font, self.max_width))

        if not lines:
            return

        line_height = font.get_height() + 4
        width = min(
            self.max_width + self.padding * 2,
            max(font.size(line)[0] for line in lines) + self.padding * 2,
        )
        height = len(lines) * line_height + self.padding * 2

        rect = pygame.Rect(x, y, width, height)

        if rect.right > screen.get_width() - 8:
            rect.right = screen.get_width() - 8

        if rect.bottom > screen.get_height() - 8:
            rect.bottom = screen.get_height() - 8

        pygame.draw.rect(screen, (35, 35, 44), rect, border_radius=8)
        pygame.draw.rect(screen, theme.PANEL_BORDER, rect, 1, border_radius=8)

        draw_y = rect.y + self.padding
        for line in lines:
            screen.blit(
                font.render(line, True, theme.TEXT_SECONDARY),
                (rect.x + self.padding, draw_y),
            )
            draw_y += line_height