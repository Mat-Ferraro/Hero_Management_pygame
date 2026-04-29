from pygame_ui import theme
from pygame_ui.widgets.text_block import TextBlock


class EmptyState:
    def __init__(
        self,
        title,
        description="",
        icon="",
        color=theme.TEXT_MUTED,
    ):
        self.title = title
        self.description = description
        self.icon = icon
        self.color = color

    def draw(self, screen, title_font, font, rect):
        center_x = rect.centerx
        y = rect.y + rect.height // 2 - 34

        if self.icon:
            icon_surface = title_font.render(str(self.icon), True, self.color)
            icon_rect = icon_surface.get_rect(center=(center_x, y))
            screen.blit(icon_surface, icon_rect)
            y += icon_surface.get_height() + 8

        title_surface = font.render(str(self.title), True, self.color)
        title_rect = title_surface.get_rect(center=(center_x, y))
        screen.blit(title_surface, title_rect)
        y += title_surface.get_height() + 8

        if self.description:
            block = TextBlock([self.description], color=self.color, row_spacing=20, max_lines=3)
            block.draw(
                screen=screen,
                font=font,
                x=rect.x + 24,
                y=y,
                max_width=rect.width - 48,
            )