from pygame_ui import theme
from pygame_ui.ui_helpers import wrap_text


class TextBlock:
    def __init__(
        self,
        lines=None,
        color=theme.TEXT_SECONDARY,
        row_spacing=20,
        max_lines=None,
    ):
        self.lines = list(lines or [])
        self.color = color
        self.row_spacing = row_spacing
        self.max_lines = max_lines

    def set_lines(self, lines):
        self.lines = list(lines or [])

    def draw(self, screen, font, x, y, max_width):
        drawn = 0

        for line in self.lines:
            for wrapped in wrap_text(line, font, max_width):
                if self.max_lines is not None and drawn >= self.max_lines:
                    return y

                screen.blit(font.render(wrapped, True, self.color), (x, y))
                y += self.row_spacing
                drawn += 1

        return y