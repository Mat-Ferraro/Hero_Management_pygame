import re
import pygame


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def clean_ansi_text(text) -> str:
    return ANSI_ESCAPE_RE.sub("", str(text))


def wrap_text(text, font, max_width):
    words = str(text).split(" ")
    lines = []
    current = ""

    for word in words:
        test = word if not current else f"{current} {word}"

        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def truncate_text(text, font, max_width):
    text = str(text)

    if font.size(text)[0] <= max_width:
        return text

    ellipsis = "..."
    trimmed = text

    while trimmed and font.size(trimmed + ellipsis)[0] > max_width:
        trimmed = trimmed[:-1]

    return trimmed + ellipsis


def clamp_scroll(value, item_count, visible_count):
    max_scroll = max(0, item_count - visible_count)
    return max(0, min(value, max_scroll))


def scrollbar_track_rect(panel, width=8, margin=14):
    return pygame.Rect(
        panel.rect.right - margin - width,
        panel.rect.y + 50,
        width,
        panel.rect.height - 82,
    )


def draw_scrollbar(
    screen,
    font,
    panel,
    scroll,
    item_count,
    visible_count,
    width=8,
    margin=14,
    show_hint=True,
):
    track_rect = scrollbar_track_rect(panel, width=width, margin=margin)

    pygame.draw.rect(screen, (44, 44, 54), track_rect, border_radius=4)

    if item_count <= visible_count:
        pygame.draw.rect(screen, (72, 72, 88), track_rect, border_radius=4)
        return

    max_scroll = max(1, item_count - visible_count)
    thumb_height = max(28, int(track_rect.height * (visible_count / item_count)))
    scroll_ratio = scroll / max_scroll
    thumb_y = track_rect.y + int((track_rect.height - thumb_height) * scroll_ratio)

    thumb_rect = pygame.Rect(track_rect.x, thumb_y, track_rect.width, thumb_height)
    pygame.draw.rect(screen, (120, 120, 150), thumb_rect, border_radius=4)

    if show_hint:
        hint = f"{scroll + 1}-{min(scroll + visible_count, item_count)} of {item_count}"
        screen.blit(
            font.render(hint, True, (160, 160, 175)),
            (panel.rect.right - 118, panel.rect.bottom - 24),
        )