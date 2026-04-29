import pygame

from pygame_ui import theme


class StatBadge:
    def __init__(
        self,
        rect,
        label,
        value,
        subtext="",
        fill_color=(48, 48, 62),
        border_color=(150, 150, 190),
    ):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.value = value
        self.subtext = subtext
        self.fill_color = fill_color
        self.border_color = border_color

    def draw(self, screen, label_font, value_font, subtext_font=None):
        subtext_font = subtext_font or label_font

        pygame.draw.rect(screen, self.fill_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, self.border_color, self.rect, 2, border_radius=8)

        screen.blit(
            label_font.render(str(self.label), True, theme.TEXT_MUTED),
            (self.rect.x + 14, self.rect.y + 8),
        )

        screen.blit(
            value_font.render(str(self.value), True, (245, 235, 210)),
            (self.rect.x + 14, self.rect.y + 26),
        )

        if self.subtext:
            screen.blit(
                subtext_font.render(str(self.subtext), True, (190, 220, 190)),
                (self.rect.x + 14, self.rect.y + 50),
            )