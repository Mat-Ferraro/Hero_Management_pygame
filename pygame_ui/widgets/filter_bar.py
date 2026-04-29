import pygame

from pygame_ui import theme
from pygame_ui.widgets.status_chip import STATUS_STYLES


class FilterBar:
    def __init__(
        self,
        rect,
        options,
        selected=None,
        on_change=None,
        allow_all=True,
    ):
        self.rect = pygame.Rect(rect)
        self.options = list(options or [])
        self.selected = selected
        self.on_change = on_change
        self.allow_all = allow_all

    def labels(self):
        if self.allow_all:
            return ["All"] + self.options

        return self.options

    def option_rects(self):
        rects = []
        x = self.rect.x

        for label in self.labels():
            width = max(64, len(str(label)) * 9 + 24)
            rects.append((label, pygame.Rect(x, self.rect.y, width, self.rect.height)))
            x += width + 8

        return rects

    def handle_event(self, event):
        if event.type != pygame.MOUSEBUTTONUP or getattr(event, "button", None) != 1:
            return False

        for label, rect in self.option_rects():
            if rect.collidepoint(event.pos):
                self.selected = None if label == "All" else label

                if self.on_change:
                    self.on_change(self.selected)

                return True

        return False

    def draw(self, screen, font, mouse_pos):
        for label, rect in self.option_rects():
            is_selected = (label == "All" and self.selected is None) or label == self.selected
            is_hovered = rect.collidepoint(mouse_pos)

            if is_selected:
                colors = STATUS_STYLES["info"]
            elif is_hovered:
                colors = STATUS_STYLES["default"]
            else:
                colors = {
                    "fill": theme.ROW_DARK,
                    "border": theme.ROW_DARK_BORDER,
                    "text": theme.TEXT_MUTED,
                }

            pygame.draw.rect(screen, colors["fill"], rect, border_radius=999)
            pygame.draw.rect(screen, colors["border"], rect, 1, border_radius=999)

            text_surface = font.render(str(label), True, colors["text"])
            text_rect = text_surface.get_rect(center=rect.center)
            screen.blit(text_surface, text_rect)