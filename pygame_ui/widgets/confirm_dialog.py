import pygame

from pygame_ui import theme
from pygame_ui.widgets.button import Button
from pygame_ui.widgets.text_block import TextBlock


class ConfirmDialog:
    def __init__(
        self,
        rect=(390, 230, 500, 250),
        title="Confirm",
        message="Are you sure?",
        confirm_text="Confirm",
        cancel_text="Cancel",
        on_confirm=None,
        on_cancel=None,
    ):
        self.rect = pygame.Rect(rect)
        self.title = title
        self.message = message
        self.confirm_text = confirm_text
        self.cancel_text = cancel_text
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.visible = False

    def show(self, title=None, message=None, on_confirm=None, on_cancel=None):
        if title is not None:
            self.title = title

        if message is not None:
            self.message = message

        if on_confirm is not None:
            self.on_confirm = on_confirm

        if on_cancel is not None:
            self.on_cancel = on_cancel

        self.visible = True

    def hide(self):
        self.visible = False

    def buttons(self):
        return [
            Button((self.rect.x + 90, self.rect.bottom - 62, 140, 40), self.cancel_text, self.cancel),
            Button((self.rect.right - 230, self.rect.bottom - 62, 140, 40), self.confirm_text, self.confirm),
        ]

    def confirm(self):
        self.visible = False

        if self.on_confirm:
            self.on_confirm()

    def cancel(self):
        self.visible = False

        if self.on_cancel:
            self.on_cancel()

    def handle_event(self, event):
        if not self.visible:
            return False

        if event.type == pygame.MOUSEBUTTONUP and getattr(event, "button", None) == 1:
            for button in self.buttons():
                if button.rect.collidepoint(event.pos):
                    button.on_click()
                    return True

            return True

        return self.visible

    def draw(self, screen, title_font, font, mouse_pos):
        if not self.visible:
            return

        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, theme.PANEL_BG, self.rect, border_radius=12)
        pygame.draw.rect(screen, theme.PANEL_BORDER, self.rect, 2, border_radius=12)

        screen.blit(
            title_font.render(self.title, True, theme.TEXT_PRIMARY),
            (self.rect.x + 24, self.rect.y + 20),
        )

        text_block = TextBlock([self.message], color=theme.TEXT_SECONDARY, row_spacing=22)
        text_block.draw(
            screen=screen,
            font=font,
            x=self.rect.x + 24,
            y=self.rect.y + 70,
            max_width=self.rect.width - 48,
        )

        for button in self.buttons():
            button.update(mouse_pos)
            button.draw(screen, font)