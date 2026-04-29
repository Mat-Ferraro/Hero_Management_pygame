import pygame

from pygame_ui import theme


class SortDropdown:
    def __init__(
        self,
        rect,
        options,
        selected=None,
        on_change=None,
    ):
        self.rect = pygame.Rect(rect)
        self.options = list(options or [])
        self.selected = selected if selected is not None else (self.options[0] if self.options else None)
        self.on_change = on_change
        self.open = False

    def selected_label(self):
        return str(self.selected) if self.selected is not None else "Sort"

    def option_rect(self, index):
        return pygame.Rect(
            self.rect.x,
            self.rect.bottom + index * self.rect.height,
            self.rect.width,
            self.rect.height,
        )

    def handle_event(self, event):
        if event.type != pygame.MOUSEBUTTONUP or getattr(event, "button", None) != 1:
            return False

        if self.rect.collidepoint(event.pos):
            self.open = not self.open
            return True

        if self.open:
            for index, option in enumerate(self.options):
                rect = self.option_rect(index)
                if rect.collidepoint(event.pos):
                    self.selected = option
                    self.open = False

                    if self.on_change:
                        self.on_change(option)

                    return True

            self.open = False
            return True

        return False

    def draw(self, screen, font, mouse_pos):
        self.draw_box(screen, font, self.rect, self.selected_label(), self.rect.collidepoint(mouse_pos), True)

        if not self.open:
            return

        for index, option in enumerate(self.options):
            rect = self.option_rect(index)
            self.draw_box(screen, font, rect, option, rect.collidepoint(mouse_pos), False)

    def draw_box(self, screen, font, rect, text, is_hovered, is_selected):
        fill = theme.ROW_DARK_HOVER if is_hovered else theme.ROW_DARK
        border = theme.ROW_DARK_SELECTED_BORDER if is_selected else theme.ROW_DARK_BORDER

        pygame.draw.rect(screen, fill, rect, border_radius=6)
        pygame.draw.rect(screen, border, rect, 1, border_radius=6)

        suffix = " ▼" if is_selected else ""
        label = f"{text}{suffix}"

        text_surface = font.render(label, True, theme.TEXT_PRIMARY)
        text_rect = text_surface.get_rect(midleft=(rect.x + 12, rect.centery))
        screen.blit(text_surface, text_rect)