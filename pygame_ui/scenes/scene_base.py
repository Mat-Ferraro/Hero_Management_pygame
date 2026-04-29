import pygame

from pygame_ui import theme


class SceneBase:
    def __init__(self):
        self.mouse_pos = (0, 0)
        self.status_message = ""

        self.font = pygame.font.SysFont(None, 22)
        self.small_font = pygame.font.SysFont(None, 20)
        self.title_font = pygame.font.SysFont(None, 28)
        self.header_font = pygame.font.SysFont(None, 30)
        self.button_font = self.font

    def update(self, mouse_pos):
        self.mouse_pos = mouse_pos

    def clear_screen(self, screen, color=None):
        screen.fill(color or theme.SCREEN_BG)

    def is_left_click(self, event):
        return event.type == pygame.MOUSEBUTTONUP and getattr(event, "button", None) == 1

    def handle_buttons_click(self, event, buttons):
        if not self.is_left_click(event):
            return False

        for button in buttons:
            if button.rect.collidepoint(event.pos):
                button.on_click()
                return True

        return False

    def update_and_draw_buttons(self, screen, buttons, font=None):
        draw_font = font or self.button_font

        for button in buttons:
            button.update(self.mouse_pos)
            button.draw(screen, draw_font)