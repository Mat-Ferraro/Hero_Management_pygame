from pygame_ui import theme
from pygame_ui.widgets.label_value_text import LabelValueText


class ResourceHeader:
    def __init__(
        self,
        resources,
        spacing=210,
        item_max_width=180,
        font_size=28,
        label_color=None,
        value_color=None,
        label_bold=True,
        value_bold=True,
    ):
        self.resources = resources
        self.spacing = spacing
        self.item_max_width = item_max_width
        self.font_size = font_size
        self.label_color = label_color or theme.TEXT_MUTED
        self.value_color = value_color or theme.TEXT_PRIMARY
        self.label_bold = label_bold
        self.value_bold = value_bold

    def draw(self, screen, font, x, y):
        current_x = x

        for label, value in self.resources:
            LabelValueText(
                label=label,
                value=value,
                separator=": ",
                label_color=self.label_color,
                value_color=self.value_color,
                label_bold=self.label_bold,
                value_bold=self.value_bold,
                font_size=self.font_size,
            ).draw(
                screen=screen,
                font=font,
                x=current_x,
                y=y,
                max_width=self.item_max_width,
            )
            current_x += self.spacing