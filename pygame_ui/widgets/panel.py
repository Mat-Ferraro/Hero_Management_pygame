import pygame

from pygame_ui import theme


class Panel:
    def __init__(self, rect, title=""):
        self.rect = pygame.Rect(rect)
        self.title = title

    def draw(self, screen, title_font):
        pygame.draw.rect(screen, theme.PANEL_BG, self.rect, border_radius=10)
        pygame.draw.rect(screen, theme.PANEL_BORDER, self.rect, 2, border_radius=10)

        if self.title:
            title_surface = title_font.render(self.title, True, theme.TEXT_PRIMARY)
            screen.blit(title_surface, (self.rect.x + 16, self.rect.y + 12))