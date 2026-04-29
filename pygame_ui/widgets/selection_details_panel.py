from pygame_ui.widgets.details_panel import DetailsPanel


class SelectionDetailsPanel:
    def __init__(
        self,
        rect,
        title,
        empty_message="Select something to inspect.",
        left_width=540,
        right_width=540,
    ):
        self.details_panel = DetailsPanel(rect, title)
        self.empty_message = empty_message
        self.left_width = left_width
        self.right_width = right_width

    @property
    def rect(self):
        return self.details_panel.rect

    def draw(self, screen, title_font, font, left_lines=None, right_lines=None):
        left_lines = list(left_lines or [])
        right_lines = list(right_lines or [])

        if not left_lines and not right_lines:
            self.details_panel.draw_empty(
                screen=screen,
                title_font=title_font,
                font=font,
                message=self.empty_message,
            )
            return

        self.details_panel.draw_two_columns(
            screen=screen,
            title_font=title_font,
            font=font,
            left_lines=left_lines,
            right_lines=right_lines,
            left_width=self.left_width,
            right_width=self.right_width,
        )

    def draw_lines(self, screen, title_font, font, lines, max_width=None):
        self.details_panel.draw_lines(
            screen=screen,
            title_font=title_font,
            font=font,
            lines=lines,
            max_width=max_width,
        )