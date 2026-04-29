import pygame

from pygame_ui.ui_helpers import clamp_scroll, draw_scrollbar
from pygame_ui.widgets.panel import Panel


class ScrollableListPanel:
    def __init__(
        self,
        rect,
        title="",
        row_height=48,
        row_spacing=52,
        visible_rows=None,
        font=None,
        title_font=None,
        padding=14,
        title_height=52,
    ):
        self.panel = Panel(rect, title)
        self.font = font or pygame.font.SysFont(None, 22)
        self.title_font = title_font or pygame.font.SysFont(None, 28)

        self.row_height = row_height
        self.row_spacing = row_spacing
        self.visible_rows_override = visible_rows
        self.padding = padding
        self.title_height = title_height

        self.items = []
        self.scroll = 0
        self.mouse_pos = (0, 0)

    @property
    def rect(self):
        return self.panel.rect

    def set_items(self, items):
        self.items = list(items or [])
        self.clamp_scroll()

    def visible_rows(self):
        if self.visible_rows_override is not None:
            return self.visible_rows_override

        available_height = self.rect.height - self.title_height - self.padding
        return max(1, available_height // self.row_spacing)

    def visible_items(self):
        end = self.scroll + self.visible_rows()
        return self.items[self.scroll:end]

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(self.mouse_pos):
            self.scroll -= event.y
            self.clamp_scroll()
            return True

        return False

    def update(self, mouse_pos):
        self.mouse_pos = mouse_pos

    def draw(self, screen, row_drawer, selected_item=None, empty_text="Nothing to show."):
        self.panel.draw(screen, self.title_font)

        visible = self.visible_items()

        if not visible:
            screen.blit(
                self.font.render(empty_text, True, (180, 180, 190)),
                (self.rect.x + self.padding + 8, self.row_start_y() + 8),
            )
        else:
            y = self.row_start_y()
            for item in visible:
                row_rect = self.row_rect(y)
                is_selected = item is selected_item
                is_hovered = row_rect.collidepoint(self.mouse_pos)

                row_drawer(screen, item, row_rect, is_selected, is_hovered)

                y += self.row_spacing

        draw_scrollbar(
            screen=screen,
            font=self.font,
            panel=self.panel,
            scroll=self.scroll,
            item_count=len(self.items),
            visible_count=self.visible_rows(),
        )

    def row_start_y(self):
        return self.rect.y + self.title_height

    def row_rect(self, y):
        return pygame.Rect(
            self.rect.x + self.padding,
            y - 8,
            self.rect.width - (self.padding * 2) - 24,
            self.row_height,
        )

    def item_at_pos(self, pos):
        y = self.row_start_y()

        for item in self.visible_items():
            if self.row_rect(y).collidepoint(pos):
                return item

            y += self.row_spacing

        return None

    def clamp_scroll(self):
        self.scroll = clamp_scroll(
            self.scroll,
            len(self.items),
            self.visible_rows(),
        )