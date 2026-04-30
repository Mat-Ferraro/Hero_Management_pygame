import pygame

from pygame_ui import theme
from pygame_ui.ui_helpers import truncate_text, wrap_text


class LabelValueText:
    def __init__(
        self,
        label,
        value,
        separator=": ",
        label_color=None,
        value_color=None,
        separator_color=None,
        label_bold=True,
        value_bold=False,
        align="left",
        gap=0,
        font_size=None,
        line_spacing=4,
        wrap_value=True,
    ):
        self.label = str(label)
        self.value = str(value)
        self.separator = str(separator)

        self.label_color = label_color or theme.TEXT_MUTED
        self.value_color = value_color or theme.TEXT_PRIMARY
        self.separator_color = separator_color or self.label_color

        self.label_bold = label_bold
        self.value_bold = value_bold

        self.align = align
        self.gap = gap
        self.font_size = font_size
        self.line_spacing = line_spacing
        self.wrap_value = wrap_value

    def set_label(self, label):
        self.label = str(label)

    def set_value(self, value):
        self.value = str(value)

    def set_text(self, label, value):
        self.label = str(label)
        self.value = str(value)

    def _derived_font(self, fallback_font, bold=False):
        size = self.font_size or fallback_font.get_height()
        derived = pygame.font.SysFont(None, size)
        derived.set_bold(bool(bold))
        return derived

    def _resolve_fonts(self, fallback_font, label_font=None, value_font=None):
        resolved_label_font = label_font or self._derived_font(fallback_font, self.label_bold)
        resolved_value_font = value_font or self._derived_font(fallback_font, self.value_bold)
        return resolved_label_font, resolved_value_font

    def _value_lines(self, value_font, available_value_width):
        if not self.wrap_value or available_value_width is None:
            return [self.value]

        if available_value_width <= 0:
            return [""]

        wrapped = wrap_text(self.value, value_font, available_value_width)
        return wrapped or [""]

    def _layout(self, font, max_width=None, label_font=None, value_font=None):
        label_font, value_font = self._resolve_fonts(font, label_font, value_font)

        label_width = label_font.size(self.label)[0]
        separator_width = label_font.size(self.separator)[0]
        prefix_width = label_width + separator_width + self.gap

        if max_width is None:
            value_lines = [self.value]
            first_line_width = prefix_width + value_font.size(self.value)[0]
            max_line_width = first_line_width
        else:
            available_value_width = max(0, max_width - prefix_width)

            if self.wrap_value:
                value_lines = self._value_lines(value_font, available_value_width)
            else:
                value_lines = [truncate_text(self.value, value_font, available_value_width)]

            first_line_width = prefix_width + value_font.size(value_lines[0])[0]
            continuation_widths = [value_font.size(line)[0] for line in value_lines[1:]]
            max_line_width = max([first_line_width] + continuation_widths) if value_lines else first_line_width

        line_height = max(label_font.get_height(), value_font.get_height())
        line_count = max(1, len(value_lines))
        total_height = (line_count * line_height) + ((line_count - 1) * self.line_spacing)

        return {
            "label_font": label_font,
            "value_font": value_font,
            "label_width": label_width,
            "separator_width": separator_width,
            "prefix_width": prefix_width,
            "value_lines": value_lines,
            "line_height": line_height,
            "line_count": line_count,
            "width": max_line_width,
            "height": total_height,
        }

    def measure(self, font, max_width=None, label_font=None, value_font=None):
        layout = self._layout(
            font=font,
            max_width=max_width,
            label_font=label_font,
            value_font=value_font,
        )
        return layout["width"], layout["height"]

    def draw(
        self,
        screen,
        font,
        x,
        y,
        max_width=None,
        label_font=None,
        value_font=None,
    ):
        layout = self._layout(
            font=font,
            max_width=max_width,
            label_font=label_font,
            value_font=value_font,
        )

        label_font = layout["label_font"]
        value_font = layout["value_font"]
        label_width = layout["label_width"]
        separator_width = layout["separator_width"]
        prefix_width = layout["prefix_width"]
        value_lines = layout["value_lines"]
        line_height = layout["line_height"]
        total_width = layout["width"]

        draw_x = x
        if self.align == "center":
            draw_x = x - (total_width // 2)
        elif self.align == "right":
            draw_x = x - total_width

        label_surface = label_font.render(self.label, True, self.label_color)
        separator_surface = label_font.render(self.separator, True, self.separator_color)

        screen.blit(label_surface, (draw_x, y))
        screen.blit(separator_surface, (draw_x + label_width, y))

        value_x = draw_x + prefix_width

        for index, line in enumerate(value_lines):
            line_y = y + (index * (line_height + self.line_spacing))
            line_x = value_x if index == 0 else value_x

            value_surface = value_font.render(line, True, self.value_color)
            screen.blit(value_surface, (line_x, line_y))

        return layout["height"]