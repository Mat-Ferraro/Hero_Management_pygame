from pygame_ui import theme


class IconLabel:
    def __init__(self, text, icon="", color=theme.TEXT_SECONDARY, icon_color=None):
        self.text = text
        self.icon = icon
        self.color = color
        self.icon_color = icon_color or color

    def draw(self, screen, font, x, y):
        cursor_x = x

        if self.icon:
            icon_surface = font.render(str(self.icon), True, self.icon_color)
            screen.blit(icon_surface, (cursor_x, y))
            cursor_x += icon_surface.get_width() + 6

        text_surface = font.render(str(self.text), True, self.color)
        screen.blit(text_surface, (cursor_x, y))

        return cursor_x + text_surface.get_width(), y + text_surface.get_height()