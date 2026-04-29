import pygame

from pygame_ui import theme


STATUS_STYLES = {
    "default": {
        "fill": (48, 48, 62),
        "border": theme.PANEL_BORDER,
        "text": theme.TEXT_SECONDARY,
    },
    "good": {
        "fill": (42, 64, 48),
        "border": (90, 150, 100),
        "text": (190, 235, 195),
    },
    "warning": {
        "fill": (70, 60, 38),
        "border": (170, 135, 70),
        "text": (245, 220, 150),
    },
    "danger": {
        "fill": (75, 42, 42),
        "border": (170, 80, 80),
        "text": (245, 170, 170),
    },
    "info": {
        "fill": (42, 56, 70),
        "border": (80, 125, 170),
        "text": (180, 215, 245),
    },
    "locked": {
        "fill": (42, 42, 48),
        "border": (90, 90, 100),
        "text": theme.TEXT_MUTED,
    },
}


class StatusChip:
    def __init__(self, rect, text, style="default"):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.style = style

    def draw(self, screen, font):
        colors = STATUS_STYLES.get(self.style, STATUS_STYLES["default"])

        pygame.draw.rect(screen, colors["fill"], self.rect, border_radius=999)
        pygame.draw.rect(screen, colors["border"], self.rect, 1, border_radius=999)

        text_surface = font.render(str(self.text), True, colors["text"])
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)