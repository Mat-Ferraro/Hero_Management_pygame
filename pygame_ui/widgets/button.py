import pygame

from pygame_ui import theme


class Button:
    def __init__(self, rect, text, on_click):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click

        self.hovered = False
        self.pressed_inside = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed_inside = True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed_inside = self.pressed_inside
            self.pressed_inside = False

            if was_pressed_inside and self.rect.collidepoint(event.pos):
                self.on_click()

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, screen, font):
        color = theme.BUTTON_BG

        if self.pressed_inside:
            color = theme.BUTTON_BG_PRESSED
        elif self.hovered:
            color = theme.BUTTON_BG_HOVER

        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, theme.BUTTON_BORDER, self.rect, 2, border_radius=8)

        text_surface = font.render(self.text, True, theme.BUTTON_TEXT)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)