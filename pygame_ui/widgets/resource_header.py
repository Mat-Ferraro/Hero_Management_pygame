from pygame_ui.widgets.value_row import ValueRow


class ResourceHeader:
    def __init__(self, resources=None, spacing=170):
        self.resources = list(resources or [])
        self.spacing = spacing

    def set_resources(self, resources):
        self.resources = list(resources or [])

    def draw(self, screen, font, x, y):
        cursor_x = x

        for label, value in self.resources:
            ValueRow(label, value).draw(
                screen=screen,
                font=font,
                x=cursor_x,
                y=y,
                label_width=70,
            )
            cursor_x += self.spacing

        return y + font.get_height() + 4