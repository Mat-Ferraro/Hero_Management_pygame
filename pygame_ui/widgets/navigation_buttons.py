from pygame_ui import theme
from pygame_ui.widgets.button import Button


def hub_button(on_click, text="Hub"):
    return Button(theme.HUB_BUTTON_RECT, text, on_click)


def main_menu_button(on_click, rect=(950, 325, 200, 52), text="Main Menu"):
    return Button(rect, text, on_click)


def action_button(text, on_click, rect=theme.DETAIL_ACTION_BUTTON_RECT):
    return Button(rect, text, on_click)


def footer_button(text, on_click, index=0, width=190, height=42, y=642, right_margin=80, spacing=20):
    x = 1280 - right_margin - width - (index * (width + spacing))
    return Button((x, y, width, height), text, on_click)