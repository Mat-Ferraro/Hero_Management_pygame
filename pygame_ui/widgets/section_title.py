from pygame_ui import theme


class SectionTitle:
    def __init__(self, text, subtitle=None):
        self.text = text
        self.subtitle = subtitle

    def draw(self, screen, title_font, subtitle_font, x, y):
        title_surface = title_font.render(str(self.text), True, theme.TEXT_PRIMARY)
        screen.blit(title_surface, (x, y))

        next_y = y + title_surface.get_height() + 4

        if self.subtitle:
            subtitle_surface = subtitle_font.render(str(self.subtitle), True, theme.TEXT_MUTED)
            screen.blit(subtitle_surface, (x, next_y))
            next_y += subtitle_surface.get_height() + 4

        return next_y