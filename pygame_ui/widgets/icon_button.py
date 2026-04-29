import pygame

from pygame_ui import theme


class IconButton:
    def __init__(self, rect, icon, on_click, tooltip=""):
        self.rect = pygame.Rect(rect)
        self.icon = icon
        self.on_click = on_click
        self.tooltip = tooltip
        self.hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP and getattr(event, "button", None) == 1:
            if self.rect.collidepoint(event.pos):
                self.on_click()
                return True
        return False

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, screen, font):
        fill = theme.BUTTON_BG_HOVER if self.hovered else theme.BUTTON_BG
        pygame.draw.rect(screen, fill, self.rect, border_radius=8)
        pygame.draw.rect(screen, theme.BUTTON_BORDER, self.rect, 1, border_radius=8)

        surface = font.render(str(self.icon), True, theme.BUTTON_TEXT)
        screen.blit(surface, surface.get_rect(center=self.rect.center))