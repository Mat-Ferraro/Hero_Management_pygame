import pygame

from pygame_ui import theme
from pygame_ui.widgets.text_block import TextBlock


class ListItemCard:
    def __init__(
        self,
        rect,
        title="",
        subtitle="",
        lines=None,
        selected=False,
        style="dark",
        padding=12,
    ):
        self.rect = pygame.Rect(rect)
        self.title = title
        self.subtitle = subtitle
        self.lines = list(lines or [])
        self.selected = selected
        self.style = style
        self.padding = padding

    def draw(self, screen, title_font, font, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)

        if self.style == "green":
            fill = theme.ROW_GREEN_SELECTED if self.selected else theme.ROW_GREEN_HOVER if hovered else theme.ROW_GREEN
            border = theme.ROW_GREEN_SELECTED_BORDER if self.selected else theme.ROW_GREEN_HOVER_BORDER if hovered else theme.ROW_GREEN_BORDER
        elif self.style == "brown":
            fill = theme.ROW_BROWN_SELECTED if self.selected else theme.ROW_BROWN_HOVER if hovered else theme.ROW_BROWN
            border = theme.ROW_BROWN_SELECTED_BORDER if self.selected else theme.ROW_BROWN_HOVER_BORDER if hovered else theme.ROW_BROWN_BORDER
        else:
            fill = theme.ROW_DARK_SELECTED if self.selected else theme.ROW_DARK_HOVER if hovered else theme.ROW_DARK
            border = theme.ROW_DARK_SELECTED_BORDER if self.selected else theme.ROW_DARK_HOVER_BORDER if hovered else theme.ROW_DARK_BORDER

        pygame.draw.rect(screen, fill, self.rect, border_radius=10)
        pygame.draw.rect(screen, border, self.rect, 2 if self.selected else 1, border_radius=10)

        y = self.rect.y + self.padding

        if self.title:
            screen.blit(title_font.render(str(self.title), True, theme.TEXT_PRIMARY), (self.rect.x + self.padding, y))
            y += title_font.get_height() + 2

        if self.subtitle:
            screen.blit(font.render(str(self.subtitle), True, theme.TEXT_MUTED), (self.rect.x + self.padding, y))
            y += font.get_height() + 4

        TextBlock(self.lines, color=theme.TEXT_SECONDARY, row_spacing=font.get_height() + 2).draw(
            screen=screen,
            font=font,
            x=self.rect.x + self.padding,
            y=y,
            max_width=self.rect.width - self.padding * 2,
        )