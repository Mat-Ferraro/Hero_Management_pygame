import pygame

from pygame_ui import theme


class Panel:
    def __init__(
        self,
        rect,
        title: str = "",
        fill_color=None,
        border_color=None,
        padding: int = 16,
        border_radius: int = 10,
    ):
        self.rect = pygame.Rect(rect)
        self.title = title
        self.fill_color = fill_color if fill_color is not None else theme.PANEL_BG
        self.border_color = border_color if border_color is not None else theme.PANEL_BORDER
        self.padding = int(padding)
        self.border_radius = int(border_radius)

    def content_rect(self, title_font=None):
        top_padding = self.padding

        if self.title and title_font is not None:
            title_height = title_font.get_height()
            top_padding += title_height + 10

        return pygame.Rect(
            self.rect.x + self.padding,
            self.rect.y + top_padding,
            max(0, self.rect.width - (self.padding * 2)),
            max(0, self.rect.height - top_padding - self.padding),
        )

    def draw(self, screen, title_font, body_font=None):
        pygame.draw.rect(
            screen,
            self.fill_color,
            self.rect,
            border_radius=self.border_radius,
        )
        pygame.draw.rect(
            screen,
            self.border_color,
            self.rect,
            2,
            border_radius=self.border_radius,
        )

        if self.title:
            title_surface = title_font.render(self.title, True, theme.TEXT_PRIMARY)
            screen.blit(
                title_surface,
                (self.rect.x + self.padding, self.rect.y + self.padding - 2),
            )