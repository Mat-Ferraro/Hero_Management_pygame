import pygame

from pygame_ui import theme
from pygame_ui.widgets.text_block import TextBlock


class StateOverlay:
    def __init__(self, title="", message=""):
        self.title = title
        self.message = message
        self.visible = False

    def show(self, title=None, message=None):
        if title is not None:
            self.title = title

        if message is not None:
            self.message = message

        self.visible = True

    def hide(self):
        self.visible = False

    def draw(self, screen, title_font, font):
        if not self.visible:
            return

        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, 0))

        rect = pygame.Rect(390, 260, 500, 180)
        pygame.draw.rect(screen, theme.PANEL_BG, rect, border_radius=12)
        pygame.draw.rect(screen, theme.PANEL_BORDER, rect, 2, border_radius=12)

        screen.blit(title_font.render(self.title, True, theme.TEXT_PRIMARY), (rect.x + 24, rect.y + 24))

        TextBlock([self.message], color=theme.TEXT_SECONDARY).draw(
            screen=screen,
            font=font,
            x=rect.x + 24,
            y=rect.y + 74,
            max_width=rect.width - 48,
        )