import pygame

from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.ui_helpers import truncate_text
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.key_value_grid import KeyValueGrid
from pygame_ui.widgets.navigation_buttons import action_button, hub_button
from pygame_ui.widgets.resource_header import ResourceHeader
from pygame_ui.widgets.selection_details_panel import SelectionDetailsPanel
from pygame_ui.widgets.stat_badge import StatBadge
from pygame_ui.widgets.status_chip import StatusChip
from pygame_ui.widgets.text_block import TextBlock
from pygame_ui.widgets.row_styles import draw_selectable_row
from pygame_ui.widgets.scrollable_list_panel import ScrollableListPanel
from pygame_ui.widgets.scrollable_text_panel import ScrollableTextPanel
from systems.training_system import can_train_hero, train_hero, training_cost, training_xp


class TrainingScene(SceneBase):
    def __init__(self, state, on_return_to_hub, on_save_game):
        super().__init__()

        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        self.status_message = "Select a hero to train."
        self.selected_hero = None
        self.stat_font = pygame.font.SysFont(None, 30)

        self.details_panel = SelectionDetailsPanel(
            rect=(1220, 150, 660, 300),
            title="Training Details",
            empty_message="Select a hero to inspect training results.",
            left_width=260,
            right_width=240,
        )

        self.footer_panel = SelectionDetailsPanel(
            rect=(40, 790, 1840, 230),
            title="Career Notes",
            empty_message="",
            left_width=860,
            right_width=860,
        )

        self.heroes_panel = ScrollableListPanel(
            rect=(40, 150, 1140, 600),
            title="Roster",
            row_height=72,
            row_gap=10,
            visible_rows=None,
            font=self.font,
            title_font=self.title_font,
            padding=18,
            title_height=64,
        )

        self.log_panel = ScrollableTextPanel(
            rect=(1220, 480, 660, 270),
            title="Training Log",
            font=self.small_font,
            title_font=self.title_font,
            row_spacing=24,
            padding=24,
            title_height=54,
        )
        self.log_panel.set_lines(["Training Hall opened."])

    def sync_lists(self):
        self.heroes_panel.set_items(self.state.roster)

    def handle_event(self, event):
        self.sync_lists()

        if self.heroes_panel.handle_event(event):
            return

        if self.log_panel.handle_event(event):
            return

        if self.handle_buttons_click(event, self.build_buttons()):
            return

        if self.is_left_click(event):
            self.handle_row_click(event.pos)

    def update(self, mouse_pos):
        super().update(mouse_pos)
        self.sync_lists()
        self.heroes_panel.update(mouse_pos)
        self.log_panel.update(mouse_pos)

    def draw(self, screen):
        self.sync_lists()
        self.clear_screen(screen)

        self.draw_header(screen)

        self.heroes_panel.draw(
            screen=screen,
            row_drawer=self.draw_hero_row,
            selected_item=self.selected_hero,
            empty_text="No heroes available.",
        )

        self.draw_details(screen)
        self.log_panel.draw(screen)
        self.draw_footer(screen)
        self.update_and_draw_buttons(screen, self.build_buttons())

    def draw_header(self, screen):
        level = self.state.guild_upgrades.training_hall_level
        cost = training_cost(level)
        xp = training_xp(level)

        HeaderPanel(
            rect=(40, 30, 1840, 96),
            title="Training Hall",
            stats="",
            status_message=self.status_message,
            stats_pos=(70, 70),
            status_pos=(1080, 108),
        ).draw(screen, self.title_font, self.header_font, self.font)

        ResourceHeader(
            resources=[
                ("Gold", f"{self.state.gold}g"),
                ("Hall", f"Lv {level}"),
                ("Cost", f"{cost}g"),
                ("XP", xp),
                ("Roster", len(self.state.roster)),
            ],
            spacing=190,
            item_max_width=170,
            font_size=24,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=False,
            value_bold=True,
        ).draw(screen, self.font, 60, 72)

    def draw_hero_row(self, screen, hero, row_rect, is_selected, is_hovered):
        allowed, reason = can_train_hero(hero)

        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style="green" if allowed else "brown",
        )

        subclass = hero.subclass or "Base"

        screen.blit(
            self.font.render(
                truncate_text(
                    f"{hero.name} | {hero.hero_class}/{subclass} | Lv {hero.level}",
                    self.font,
                    row_rect.width - 250,
                ),
                True,
                (210, 240, 210) if allowed else theme.TEXT_MUTED,
            ),
            (row_rect.x + 14, row_rect.y + 10),
        )

        StatusChip(
            rect=(row_rect.right - 230, row_rect.y + 10, 104, 26),
            text="Trainable" if allowed else "Blocked",
            style="good" if allowed else "danger",
        ).draw(screen, self.small_font)

        StatusChip(
            rect=(row_rect.right - 116, row_rect.y + 10, 102, 26),
            text=f"XP {hero.xp}",
            style="info",
        ).draw(screen, self.small_font)

        detail = (
            f"Age {hero.age} ({hero.career_stage()}) | "
            f"Pwr {hero.combat_power()} | Mentor {hero.mentorship_value()} | "
            f"Next Lv {hero.xp_to_next_level()}"
        )

        if not allowed:
            detail += f" | {reason}"

        TextBlock(
            lines=[detail],
            color=(180, 210, 180) if allowed else theme.TEXT_MUTED,
            row_spacing=20,
            max_lines=1,
        ).draw(
            screen=screen,
            font=self.small_font,
            x=row_rect.x + 14,
            y=row_rect.y + 46,
            max_width=row_rect.width - 28,
        )

    def draw_details(self, screen):
        level = self.state.guild_upgrades.training_hall_level
        cost = training_cost(level)
        xp = training_xp(level)

        self.details_panel.details_panel.panel.draw(screen, self.title_font)

        StatBadge(
            rect=(self.details_panel.rect.right - 170, self.details_panel.rect.y + 56, 140, 78),
            label="Cost",
            value=f"{cost}g",
            subtext=f"+{xp} XP",
        ).draw(screen, self.small_font, self.stat_font, self.small_font)

        if self.selected_hero is None:
            TextBlock(
                lines=["Select a hero to inspect training results."],
                color=theme.TEXT_SECONDARY,
                row_spacing=24,
            ).draw(
                screen=screen,
                font=self.font,
                x=self.details_panel.rect.x + 30,
                y=self.details_panel.rect.y + 70,
                max_width=self.details_panel.rect.width - 230,
            )
            return

        hero = self.selected_hero
        allowed, reason = can_train_hero(hero)

        KeyValueGrid(
            rows=[
                ("Hero", hero.name),
                ("Class", hero.hero_class),
                ("Subclass", hero.subclass or "None"),
                ("Ability", hero.special_ability or "None"),
                ("Status", "Ready" if allowed else reason),
                ("Level", hero.level),
                ("XP", f"{hero.xp}/{hero.xp_to_next_level()}"),
                ("Power", hero.combat_power()),
                ("Mentor", hero.mentorship_value()),
                ("Age", hero.age),
            ],
            columns=2,
            column_width=270,
            column_gap=24,
            row_gap=12,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=True,
            value_bold=False,
            font_size=22,
            line_spacing=2,
        ).draw(
            screen=screen,
            font=self.font,
            x=self.details_panel.rect.x + 30,
            y=self.details_panel.rect.y + 72,
        )

    def draw_footer(self, screen):
        self.footer_panel.details_panel.panel.draw(screen, self.title_font)

        left_lines = [
            "Training is safe but costs gold.",
            "Expeditions remain the fastest way to grow heroes.",
            "Training is ideal for topping off heroes close to leveling.",
        ]

        right_lines = [
            "Future Training Hall upgrades will unlock subclass choices.",
            "Older heroes may lose raw power over time.",
            "Mentorship and learned abilities can remain valuable late into a career.",
        ]

        y = self.footer_panel.rect.y + 54

        TextBlock(left_lines, color=theme.TEXT_SECONDARY, row_spacing=28).draw(
            screen=screen,
            font=self.font,
            x=self.footer_panel.rect.x + 28,
            y=y,
            max_width=820,
        )

        TextBlock(right_lines, color=theme.TEXT_SECONDARY, row_spacing=28).draw(
            screen=screen,
            font=self.font,
            x=self.footer_panel.rect.x + 960,
            y=y,
            max_width=820,
        )

    def build_buttons(self):
        buttons = [
            hub_button(self.on_return_to_hub),
        ]

        if self.selected_hero:
            allowed, _ = can_train_hero(self.selected_hero)
            label = "Train Hero" if allowed else "Cannot Train"
            buttons.append(action_button(label, self.train_selected_hero, rect=(1660, 700, 180, 44)))

        return buttons

    def handle_row_click(self, pos):
        hero = self.heroes_panel.item_at_pos(pos)
        if hero is not None:
            self.selected_hero = hero
            self.status_message = f"Selected hero: {hero.name}"

    def train_selected_hero(self):
        if self.selected_hero is None:
            self.status_message = "Select a hero first."
            return

        messages = train_hero(self.state, self.selected_hero)
        self.log_panel.append_lines(messages, auto_scroll=True)
        self.status_message = messages[-1] if messages else "Training complete."

        if self.on_save_game:
            self.on_save_game()