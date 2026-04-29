from pygame_ui import theme


class ValueRow:
    def __init__(self, label, value, label_color=theme.TEXT_MUTED, value_color=theme.TEXT_SECONDARY):
        self.label = label
        self.value = value
        self.label_color = label_color
        self.value_color = value_color

    def draw(self, screen, font, x, y, label_width=150):
        label_surface = font.render(str(self.label), True, self.label_color)
        value_surface = font.render(str(self.value), True, self.value_color)

        screen.blit(label_surface, (x, y))
        screen.blit(value_surface, (x + label_width, y))

        return y + max(label_surface.get_height(), value_surface.get_height()) + 4