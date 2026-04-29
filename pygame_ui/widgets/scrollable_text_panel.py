import pygame

from pygame_ui.ui_helpers import clean_ansi_text, clamp_scroll, draw_scrollbar, wrap_text
from pygame_ui.widgets.panel import Panel


class ScrollableTextPanel:
    def __init__(
        self,
        rect,
        title="",
        font=None,
        title_font=None,
        text_color=(210, 210, 220),
        padding=24,
        title_height=46,
        row_spacing=22,
    ):
        self.panel = Panel(rect, title)
        self.font = font or pygame.font.SysFont(None, 22)
        self.title_font = title_font or pygame.font.SysFont(None, 28)

        self.text_color = text_color
        self.padding = padding
        self.title_height = title_height
        self.row_spacing = row_spacing

        self.lines = []
        self.scroll = 0
        self.mouse_pos = (0, 0)

    @property
    def rect(self):
        return self.panel.rect

    def set_lines(self, lines, auto_scroll=False):
        self.lines = list(lines or [])
        self.clamp_scroll()

        if auto_scroll:
            self.scroll_to_bottom()

    def append_lines(self, lines, auto_scroll=True):
        if isinstance(lines, str):
            self.lines.append(lines)
        else:
            self.lines.extend(lines or [])

        self.clamp_scroll()

        if auto_scroll:
            self.scroll_to_bottom()

    def clear(self):
        self.lines = []
        self.scroll = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(self.mouse_pos):
            self.scroll -= event.y
            self.clamp_scroll()
            return True

        return False

    def update(self, mouse_pos):
        self.mouse_pos = mouse_pos

    def draw(self, screen):
        self.panel.draw(screen, self.title_font)

        content_rect = self.content_rect()
        wrapped_lines = self.wrapped_lines()
        visible_count = self.visible_count()
        visible_lines = wrapped_lines[self.scroll:self.scroll + visible_count]

        previous_clip = screen.get_clip()
        screen.set_clip(content_rect)

        y = content_rect.y
        for line in visible_lines:
            rendered = self.font.render(line, True, self.text_color)
            screen.blit(rendered, (content_rect.x, y))
            y += self.row_spacing

        screen.set_clip(previous_clip)

        draw_scrollbar(
            screen=screen,
            font=self.font,
            panel=self.panel,
            scroll=self.scroll,
            item_count=len(wrapped_lines),
            visible_count=visible_count,
        )

    def content_rect(self):
        return pygame.Rect(
            self.rect.x + self.padding,
            self.rect.y + self.title_height,
            self.rect.width - (self.padding * 2) - 26,
            self.rect.height - self.title_height - self.padding,
        )

    def wrapped_lines(self):
        content_width = self.content_rect().width
        display_lines = []

        for line in self.lines:
            clean = clean_ansi_text(line)
            wrapped = wrap_text(clean, self.font, content_width)

            if wrapped:
                display_lines.extend(wrapped)
            else:
                display_lines.append("")

        return display_lines

    def visible_count(self):
        return max(1, self.content_rect().height // self.row_spacing)

    def clamp_scroll(self):
        self.scroll = clamp_scroll(
            self.scroll,
            len(self.wrapped_lines()),
            self.visible_count(),
        )

    def scroll_to_bottom(self):
        wrapped = self.wrapped_lines()
        self.scroll = clamp_scroll(
            max(0, len(wrapped) - self.visible_count()),
            len(wrapped),
            self.visible_count(),
        )