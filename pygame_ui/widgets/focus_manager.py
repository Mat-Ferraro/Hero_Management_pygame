class FocusManager:
    def __init__(self):
        self.items = []
        self.focus_index = 0

    def set_items(self, items):
        self.items = list(items or [])
        self.focus_index = min(self.focus_index, max(0, len(self.items) - 1))

    def focused_item(self):
        if not self.items:
            return None
        return self.items[self.focus_index]

    def move_next(self):
        if self.items:
            self.focus_index = (self.focus_index + 1) % len(self.items)

    def move_previous(self):
        if self.items:
            self.focus_index = (self.focus_index - 1) % len(self.items)

    def set_focus(self, item):
        if item in self.items:
            self.focus_index = self.items.index(item)