import pygame

from pygame_ui import theme


class HoverHighlight:
    def __init__(self, rect, selected=False, style="dark"):
        self.rect = pygame.Rect(rect)
        self.selected = selected
        self.style = style

    def colors(self, hovered=False):
        if self.style == "green":
            normal, hover, selected = theme.ROW_GREEN, theme.ROW_GREEN_HOVER, theme.ROW_GREEN_SELECTED
            border, hover_border, selected_border = theme.ROW_GREEN_BORDER, theme.ROW_GREEN_HOVER_BORDER, theme.ROW_GREEN_SELECTED_BORDER
        elif self.style == "brown":
            normal, hover, selected = theme.ROW_BROWN, theme.ROW_BROWN_HOVER, theme.ROW_BROWN_SELECTED
            border, hover_border, selected_border = theme.ROW_BROWN_BORDER, theme.ROW_BROWN_HOVER_BORDER, theme.ROW_BROWN_SELECTED_BORDER
        else:
            normal, hover, selected = theme.ROW_DARK, theme.ROW_DARK_HOVER, theme.ROW_DARK_SELECTED
            border, hover_border, selected_border = theme.ROW_DARK_BORDER, theme.ROW_DARK_HOVER_BORDER, theme.ROW_DARK_SELECTED_BORDER

        if self.selected:
            return selected, selected_border, 2

        if hovered:
            return hover, hover_border, 1

        return normal, border, 1

    def draw(self, screen, mouse_pos, border_radius=8):
        fill, border, width = self.colors(self.rect.collidepoint(mouse_pos))
        pygame.draw.rect(screen, fill, self.rect, border_radius=border_radius)
        pygame.draw.rect(screen, border, self.rect, width, border_radius=border_radius)