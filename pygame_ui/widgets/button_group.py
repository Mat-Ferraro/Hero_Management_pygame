from pygame_ui.widgets.button import Button


class ButtonGroup:
    def __init__(self, buttons=None):
        self.buttons = buttons or []

    def add(self, rect, text, on_click):
        self.buttons.append(Button(rect, text, on_click))

    def extend(self, buttons):
        self.buttons.extend(buttons)

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def update(self, mouse_pos):
        for button in self.buttons:
            button.update(mouse_pos)

    def draw(self, screen, font):
        for button in self.buttons:
            button.draw(screen, font)

    def clicked(self, event):
        if not hasattr(event, "pos"):
            return False

        for button in self.buttons:
            if button.rect.collidepoint(event.pos):
                button.on_click()
                return True

        return False