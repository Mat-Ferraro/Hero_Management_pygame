import pygame

from pygame_ui import theme


class TimelineStrip:
    def __init__(
        self,
        rect,
        total_steps,
        current_step=0,
        labels=None,
        completed_color=(100, 170, 120),
        active_color=(220, 170, 100),
        pending_color=(60, 60, 70),
    ):
        self.rect = pygame.Rect(rect)
        self.total_steps = max(1, total_steps)
        self.current_step = current_step
        self.labels = list(labels or [])
        self.completed_color = completed_color
        self.active_color = active_color
        self.pending_color = pending_color

    def set_progress(self, current_step, total_steps=None, labels=None):
        self.current_step = current_step

        if total_steps is not None:
            self.total_steps = max(1, total_steps)

        if labels is not None:
            self.labels = list(labels)

    def draw(self, screen, font=None):
        step_gap = 8
        step_width = (self.rect.width - step_gap * (self.total_steps - 1)) // self.total_steps

        for index in range(self.total_steps):
            step_rect = pygame.Rect(
                self.rect.x + index * (step_width + step_gap),
                self.rect.y,
                step_width,
                self.rect.height,
            )

            if index < self.current_step:
                fill = self.completed_color
            elif index == self.current_step:
                fill = self.active_color
            else:
                fill = self.pending_color

            pygame.draw.rect(screen, fill, step_rect, border_radius=6)
            pygame.draw.rect(screen, theme.PANEL_BORDER, step_rect, 1, border_radius=6)

            if font and index < len(self.labels):
                label_surface = font.render(str(self.labels[index]), True, theme.TEXT_PRIMARY)
                label_rect = label_surface.get_rect(center=step_rect.center)
                screen.blit(label_surface, label_rect)