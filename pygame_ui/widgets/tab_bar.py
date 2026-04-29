import pygame

from pygame_ui import theme


class TabBar:
    def __init__(
        self,
        rect,
        tabs,
        selected_index=0,
        on_tab_selected=None,
    ):
        self.rect = pygame.Rect(rect)
        self.tabs = list(tabs or [])
        self.selected_index = selected_index
        self.on_tab_selected = on_tab_selected

    def tab_rects(self):
        if not self.tabs:
            return []

        tab_width = self.rect.width // len(self.tabs)
        rects = []

        for index, _tab in enumerate(self.tabs):
            rects.append(
                pygame.Rect(
                    self.rect.x + index * tab_width,
                    self.rect.y,
                    tab_width,
                    self.rect.height,
                )
            )

        return rects

    def handle_event(self, event):
        if event.type != pygame.MOUSEBUTTONUP or getattr(event, "button", None) != 1:
            return False

        for index, rect in enumerate(self.tab_rects()):
            if rect.collidepoint(event.pos):
                self.selected_index = index

                if self.on_tab_selected:
                    self.on_tab_selected(index, self.tabs[index])

                return True

        return False

    def selected_tab(self):
        if not self.tabs:
            return None

        if self.selected_index < 0 or self.selected_index >= len(self.tabs):
            return None

        return self.tabs[self.selected_index]

    def draw(self, screen, font, mouse_pos):
        for index, rect in enumerate(self.tab_rects()):
            is_selected = index == self.selected_index
            is_hovered = rect.collidepoint(mouse_pos)

            if is_selected:
                fill = theme.ROW_DARK_SELECTED
                border = theme.ROW_DARK_SELECTED_BORDER
            elif is_hovered:
                fill = theme.ROW_DARK_HOVER
                border = theme.ROW_DARK_HOVER_BORDER
            else:
                fill = theme.ROW_DARK
                border = theme.ROW_DARK_BORDER

            pygame.draw.rect(screen, fill, rect, border_radius=8)
            pygame.draw.rect(screen, border, rect, 1, border_radius=8)

            label = str(self.tabs[index])
            label_surface = font.render(label, True, theme.TEXT_PRIMARY)
            label_rect = label_surface.get_rect(center=rect.center)
            screen.blit(label_surface, label_rect)