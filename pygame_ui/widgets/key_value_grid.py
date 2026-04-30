from pygame_ui import theme
from pygame_ui.widgets.label_value_text import LabelValueText


class KeyValueGrid:
    def __init__(
        self,
        rows=None,
        columns=2,
        label_width=None,
        column_width=280,
        column_gap=0,
        row_gap=10,
        row_spacing=None,
        label_color=None,
        value_color=None,
        label_bold=True,
        value_bold=False,
        font_size=22,
        line_spacing=2,
        separator=": ",
    ):
        self.rows = list(rows or [])
        self.columns = max(1, columns)

        # Backward compatibility
        self.label_width = label_width
        self.column_width = column_width
        self.column_gap = column_gap

        # Support old row_spacing name and new row_gap name
        if row_spacing is not None:
            self.row_gap = row_spacing
        else:
            self.row_gap = row_gap

        self.label_color = label_color or theme.TEXT_MUTED
        self.value_color = value_color or theme.TEXT_SECONDARY
        self.label_bold = label_bold
        self.value_bold = value_bold
        self.font_size = font_size
        self.line_spacing = line_spacing
        self.separator = separator

    def set_rows(self, rows):
        self.rows = list(rows or [])

    def draw(self, screen, font, x, y):
        if not self.rows:
            return y

        column_heights = [y for _ in range(self.columns)]

        for index, row in enumerate(self.rows):
            label, value = row

            column = index % self.columns
            cell_x = x + column * (self.column_width + self.column_gap)
            cell_y = column_heights[column]

            widget = LabelValueText(
                label=label,
                value=value,
                separator=self.separator,
                label_color=self.label_color,
                value_color=self.value_color,
                label_bold=self.label_bold,
                value_bold=self.value_bold,
                font_size=self.font_size,
                line_spacing=self.line_spacing,
                wrap_value=True,
            )

            used_height = widget.draw(
                screen=screen,
                font=font,
                x=cell_x,
                y=cell_y,
                max_width=self.column_width,
            )

            column_heights[column] += used_height + self.row_gap

        return max(column_heights)