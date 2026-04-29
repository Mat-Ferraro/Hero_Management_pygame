from pygame_ui import theme


class KeyValueGrid:
    def __init__(
        self,
        rows=None,
        columns=2,
        label_width=110,
        column_width=280,
        row_spacing=22,
    ):
        self.rows = list(rows or [])
        self.columns = max(1, columns)
        self.label_width = label_width
        self.column_width = column_width
        self.row_spacing = row_spacing

    def set_rows(self, rows):
        self.rows = list(rows or [])

    def draw(self, screen, font, x, y):
        for index, row in enumerate(self.rows):
            label, value = row

            column = index % self.columns
            row_index = index // self.columns

            cell_x = x + column * self.column_width
            cell_y = y + row_index * self.row_spacing

            screen.blit(
                font.render(str(label), True, theme.TEXT_MUTED),
                (cell_x, cell_y),
            )

            screen.blit(
                font.render(str(value), True, theme.TEXT_SECONDARY),
                (cell_x + self.label_width, cell_y),
            )

        total_rows = (len(self.rows) + self.columns - 1) // self.columns
        return y + total_rows * self.row_spacing