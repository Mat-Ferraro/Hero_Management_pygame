import pygame

from pygame_ui import theme


ROW_THEMES = {
    "dark": {
        "normal": theme.ROW_DARK,
        "hover": theme.ROW_DARK_HOVER,
        "selected": theme.ROW_DARK_SELECTED,
        "border": theme.ROW_DARK_BORDER,
        "hover_border": theme.ROW_DARK_HOVER_BORDER,
        "selected_border": theme.ROW_DARK_SELECTED_BORDER,
    },
    "green": {
        "normal": theme.ROW_GREEN,
        "hover": theme.ROW_GREEN_HOVER,
        "selected": theme.ROW_GREEN_SELECTED,
        "border": theme.ROW_GREEN_BORDER,
        "hover_border": theme.ROW_GREEN_HOVER_BORDER,
        "selected_border": theme.ROW_GREEN_SELECTED_BORDER,
    },
    "brown": {
        "normal": theme.ROW_BROWN,
        "hover": theme.ROW_BROWN_HOVER,
        "selected": theme.ROW_BROWN_SELECTED,
        "border": theme.ROW_BROWN_BORDER,
        "hover_border": theme.ROW_BROWN_HOVER_BORDER,
        "selected_border": theme.ROW_BROWN_SELECTED_BORDER,
    },
}


def draw_selectable_row(screen, rect, is_selected=False, is_hovered=False, style="dark", border_radius=8):
    colors = ROW_THEMES.get(style, ROW_THEMES["dark"])

    if is_selected:
        fill_color = colors["selected"]
        border_color = colors["selected_border"]
        border_width = 2
    elif is_hovered:
        fill_color = colors["hover"]
        border_color = colors["hover_border"]
        border_width = 1
    else:
        fill_color = colors["normal"]
        border_color = colors["border"]
        border_width = 1

    pygame.draw.rect(screen, fill_color, rect, border_radius=border_radius)
    pygame.draw.rect(screen, border_color, rect, border_width, border_radius=border_radius)