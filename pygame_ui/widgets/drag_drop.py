class DragDropController:
    def __init__(self):
        self.dragging_item = None
        self.drag_origin = None
        self.drag_pos = (0, 0)

    def start_drag(self, item, origin, pos):
        self.dragging_item = item
        self.drag_origin = origin
        self.drag_pos = pos

    def update(self, pos):
        self.drag_pos = pos

    def drop(self):
        item = self.dragging_item
        origin = self.drag_origin
        pos = self.drag_pos
        self.clear()
        return item, origin, pos

    def clear(self):
        self.dragging_item = None
        self.drag_origin = None
        self.drag_pos = (0, 0)

    def is_dragging(self):
        return self.dragging_item is not None