class LayoutRow:
    def __init__(self, x, y, spacing=8, align="top"):
        self.x = x
        self.y = y
        self.spacing = spacing
        self.align = align
        self.cursor_x = x
        self.items = []

    def add_rect(self, width, height):
        rect = (self.cursor_x, self.y, width, height)
        self.cursor_x += width + self.spacing
        self.items.append(rect)
        return rect

    def reset(self):
        self.cursor_x = self.x
        self.items = []