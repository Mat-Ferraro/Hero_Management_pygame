import pygame

from pygame_ui import theme


class Divider:
    def __init__(self, rect, color=theme.PANEL_BORDER):
        self.rect = pygame.Rect(rect)
        self.color = color

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)