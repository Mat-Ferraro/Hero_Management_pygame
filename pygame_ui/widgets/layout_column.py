class LayoutColumn:
    def __init__(self, x, y, spacing=8):
        self.x = x
        self.y = y
        self.spacing = spacing
        self.cursor_y = y
        self.items = []

    def add_rect(self, width, height):
        rect = (self.x, self.cursor_y, width, height)
        self.cursor_y += height + self.spacing
        self.items.append(rect)
        return rect

    def add_gap(self, height):
        self.cursor_y += height

    def reset(self):
        self.cursor_y = self.y
        self.items = []