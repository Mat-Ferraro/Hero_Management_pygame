from pygame_ui import theme
from pygame_ui.widgets.panel import Panel


class HeaderPanel:
    def __init__(
        self,
        rect=theme.HEADER_RECT,
        title="",
        stats="",
        status_message="",
        stats_pos=(40, 56),
        status_pos=(740, 82),
    ):
        self.panel = Panel(rect, title)
        self.stats = stats
        self.status_message = status_message
        self.stats_pos = stats_pos
        self.status_pos = status_pos

    @property
    def rect(self):
        return self.panel.rect

    def draw(self, screen, title_font, header_font, status_font):
        self.panel.draw(screen, title_font)

        if self.stats:
            screen.blit(
                header_font.render(self.stats, True, theme.TEXT_PRIMARY),
                self.stats_pos,
            )

        if self.status_message:
            screen.blit(
                status_font.render(self.status_message, True, theme.TEXT_STATUS),
                self.status_pos,
            )