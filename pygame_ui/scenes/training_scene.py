import pygame

from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.ui_helpers import truncate_text
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.navigation_buttons import action_button, hub_button
from pygame_ui.widgets.resource_header import ResourceHeader
from pygame_ui.widgets.selection_details_panel import SelectionDetailsPanel
from pygame_ui.widgets.stat_badge import StatBadge
from pygame_ui.widgets.status_chip import StatusChip
from pygame_ui.widgets.text_block import TextBlock
from pygame_ui.widgets.row_styles import draw_selectable_row
from pygame_ui.widgets.scrollable_list_panel import ScrollableListPanel
from pygame_ui.widgets.scrollable_text_panel import ScrollableTextPanel
from systems.hero_progression import ensure_progression_fields
from systems.training_system import (
    can_specialize_hero,
    can_train_hero,
    specialize_hero,
    specialization_paths_for_hero,
)


class TrainingScene(SceneBase):
    def __init__(self, state, on_return_to_hub, on_save_game):
        super().__init__()

        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        self.status_message = "Select a hero to specialize."
        self.selected_hero = None
        self.selected_path_name = None
        self.stat_font = pygame.font.SysFont(None, 30)

        self.details_panel = SelectionDetailsPanel(
            rect=(1220, 150, 660, 300),
            title="Training Details",
            empty_message="Select a hero to inspect specialization details.",
            left_width=260,
            right_width=240,
        )

        self.footer_panel = SelectionDetailsPanel(
            rect=(40, 790, 1840, 230),
            title="Training Paths",
            empty_message="",
            left_width=920,
            right_width=840,
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
        for hero in self.state.roster:
            ensure_progression_fields(hero)
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
            self.handle_path_click(event.pos)

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
                ("Roster", len(self.state.roster)),
            ],
            spacing=220,
        ).draw(screen, self.font, 60, 72)

    def draw_hero_row(self, screen, hero, row_rect, is_selected, is_hovered):
        ensure_progression_fields(hero)
        allowed, reason = can_train_hero(hero)

        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style="green" if allowed else "brown",
        )

        subclass = hero.primary_subclass or hero.subclass or "Base"

        screen.blit(
            self.font.render(
                truncate_text(
                    f"{hero.name} | {hero.hero_class}/{subclass} | Lv {hero.level}",
                    self.font,
                    row_rect.width - 340,
                ),
                True,
                (210, 240, 210) if allowed else theme.TEXT_MUTED,
            ),
            (row_rect.x + 14, row_rect.y + 10),
        )

        StatusChip(
            rect=(row_rect.right - 340, row_rect.y + 10, 104, 26),
            text="Ready" if allowed else "Blocked",
            style="good" if allowed else "danger",
        ).draw(screen, self.small_font)

        StatusChip(
            rect=(row_rect.right - 226, row_rect.y + 10, 102, 26),
            text=f"XP {hero.xp}",
            style="info",
        ).draw(screen, self.small_font)

        StatusChip(
            rect=(row_rect.right - 114, row_rect.y + 10, 100, 26),
            text=f"TP {hero.training_points}",
            style="warning" if hero.training_points > 0 else "default",
        ).draw(screen, self.small_font)

        detail = (
            f"Age {hero.age} ({hero.career_stage()}) | "
            f"Pwr {hero.combat_power()} | Mentor {hero.mentorship_value()} | "
            f"Subclasses {len(hero.unlocked_subclasses)}"
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

        self.details_panel.details_panel.panel.draw(screen, self.title_font)

        StatBadge(
            rect=(self.details_panel.rect.right - 170, self.details_panel.rect.y + 56, 140, 78),
            label="Hall",
            value=f"Lv {level}",
            subtext="Specialization",
        ).draw(screen, self.small_font, self.stat_font, self.small_font)

        if self.selected_hero is None:
            TextBlock(
                lines=["Select a hero to inspect specialization details."],
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
        ensure_progression_fields(hero)
        allowed, reason = can_train_hero(hero)

        subclass_text = ", ".join(hero.unlocked_subclasses) if hero.unlocked_subclasses else "None"
        ability_text = ", ".join(hero.unlocked_abilities) if hero.unlocked_abilities else "None"

        left_lines = [
            f"Hero: {hero.name}",
            f"Class: {hero.hero_class}",
            f"Primary: {hero.primary_subclass or hero.subclass or 'None'}",
            f"Status: {'Ready' if allowed else reason}",
            f"Training Points: {hero.training_points}",
        ]

        right_lines = [
            f"Level: {hero.level}",
            f"XP: {hero.xp}/{hero.xp_to_next_level()}",
            f"Power: {hero.combat_power()}",
            f"Subclasses: {subclass_text}",
            f"Abilities: {ability_text}",
        ]

        start_x = self.details_panel.rect.x + 30
        start_y = self.details_panel.rect.y + 72
        column_width = 300

        for line in left_lines:
            screen.blit(self.font.render(line, True, theme.TEXT_SECONDARY), (start_x, start_y))
            start_y += 28

        right_x = self.details_panel.rect.x + column_width
        right_y = self.details_panel.rect.y + 72

        for line in right_lines:
            for wrapped in self.wrap_lines(line, 300):
                screen.blit(self.font.render(wrapped, True, theme.TEXT_SECONDARY), (right_x, right_y))
                right_y += 24

    def draw_footer(self, screen):
        self.footer_panel.details_panel.panel.draw(screen, self.title_font)

        if self.selected_hero is None:
            left_lines = [
                "Heroes gain training points from missions.",
                "Specialization spends training points.",
                "Select a hero to inspect available paths.",
            ]
            right_lines = [
                "At Training Hall Lv 3, heroes can begin specializing.",
                "Each path grants stats and unlocks a subclass at rank 3.",
                "Heroes can unlock multiple subclasses over time.",
            ]
            y = self.footer_panel.rect.y + 54

            TextBlock(left_lines, color=theme.TEXT_SECONDARY, row_spacing=28).draw(
                screen=screen,
                font=self.font,
                x=self.footer_panel.rect.x + 28,
                y=y,
                max_width=860,
            )

            TextBlock(right_lines, color=theme.TEXT_SECONDARY, row_spacing=28).draw(
                screen=screen,
                font=self.font,
                x=self.footer_panel.rect.x + 960,
                y=y,
                max_width=820,
            )
            return

        hero = self.selected_hero
        ensure_progression_fields(hero)

        unlocked_subclasses = ", ".join(hero.unlocked_subclasses) if hero.unlocked_subclasses else "None"
        unlocked_abilities = ", ".join(hero.unlocked_abilities) if hero.unlocked_abilities else "None"

        left_lines = [
            "Specialization spends training points.",
            f"Training Points Available: {hero.training_points}",
            f"Unlocked Subclasses: {unlocked_subclasses}",
        ]

        if self.state.guild_upgrades.training_hall_level < 3:
            right_lines = [
                "Specialization is locked until Training Hall Lv 3.",
                "Keep upgrading your guild.",
                "Path choices will appear once the hall is advanced enough.",
            ]
            y = self.footer_panel.rect.y + 54

            TextBlock(left_lines, color=theme.TEXT_SECONDARY, row_spacing=28).draw(
                screen=screen,
                font=self.font,
                x=self.footer_panel.rect.x + 28,
                y=y,
                max_width=860,
            )

            TextBlock(right_lines, color=theme.TEXT_SECONDARY, row_spacing=28).draw(
                screen=screen,
                font=self.font,
                x=self.footer_panel.rect.x + 960,
                y=y,
                max_width=820,
            )
            return

        paths = specialization_paths_for_hero(hero)
        y = self.footer_panel.rect.y + 54

        TextBlock(left_lines, color=theme.TEXT_SECONDARY, row_spacing=28).draw(
            screen=screen,
            font=self.font,
            x=self.footer_panel.rect.x + 28,
            y=y,
            max_width=500,
        )

        abilities_y = y + 92
        TextBlock(
            lines=[f"Unlocked Abilities: {unlocked_abilities}"],
            color=theme.TEXT_SECONDARY,
            row_spacing=24,
        ).draw(
            screen=screen,
            font=self.small_font,
            x=self.footer_panel.rect.x + 28,
            y=abilities_y,
            max_width=500,
        )

        section_x = self.footer_panel.rect.x + 520
        section_y = self.footer_panel.rect.y + 54
        title = self.font.render("Choose a Path", True, theme.TEXT_PRIMARY)
        screen.blit(title, (section_x, section_y))

        for path_name in paths.keys():
            rect = self.path_button_rect(path_name)
            is_selected = self.selected_path_name == path_name

            fill_color = (62, 74, 92) if is_selected else (48, 48, 58)
            border_color = (135, 160, 210) if is_selected else (98, 102, 120)

            pygame.draw.rect(screen, fill_color, rect, border_radius=10)
            pygame.draw.rect(screen, border_color, rect, 1, border_radius=10)

            rank = int(hero.training_path_progress.get(path_name, 0))
            can_spec, reason = can_specialize_hero(hero, path_name)

            screen.blit(self.font.render(path_name, True, theme.TEXT_PRIMARY), (rect.x + 12, rect.y + 10))
            screen.blit(self.small_font.render(f"Rank {rank}/3", True, theme.TEXT_MUTED), (rect.x + 12, rect.y + 38))

            chip_text = "Ready" if can_spec else "Locked"
            chip_style = "good" if can_spec else "default"
            StatusChip(
                rect=(rect.right - 96, rect.y + 10, 82, 22),
                text=chip_text,
                style=chip_style,
            ).draw(screen, self.small_font)

            if path_name == self.selected_path_name:
                reward_text = self.next_rank_summary(hero, path_name)
                reason_text = "Spend 1 TP" if can_spec else reason
                screen.blit(
                    self.small_font.render(truncate_text(reward_text, self.small_font, rect.width - 24), True, theme.TEXT_SECONDARY),
                    (rect.x + 12, rect.y + 62),
                )
                screen.blit(
                    self.small_font.render(truncate_text(reason_text, self.small_font, rect.width - 24), True, theme.TEXT_MUTED),
                    (rect.x + 12, rect.y + 82),
                )

    def build_buttons(self):
        buttons = [
            hub_button(self.on_return_to_hub),
        ]

        if self.selected_hero and self.state.guild_upgrades.training_hall_level >= 3:
            if self.selected_path_name:
                buttons.append(
                    action_button(
                        "Specialize",
                        self.specialize_selected_hero,
                        rect=(1660, 700, 180, 44),
                    )
                )
            else:
                buttons.append(
                    action_button(
                        "Choose Path",
                        self.no_path_selected,
                        rect=(1660, 700, 180, 44),
                    )
                )

        return buttons

    def handle_row_click(self, pos):
        hero = self.heroes_panel.item_at_pos(pos)
        if hero is not None:
            self.selected_hero = hero
            self.selected_path_name = None
            self.status_message = f"Selected hero: {hero.name}"

    def handle_path_click(self, pos):
        if self.selected_hero is None:
            return

        if self.state.guild_upgrades.training_hall_level < 3:
            return

        paths = specialization_paths_for_hero(self.selected_hero)
        for path_name in paths.keys():
            rect = self.path_button_rect(path_name)
            if rect.collidepoint(pos):
                self.selected_path_name = path_name
                self.status_message = f"Selected path: {path_name}"
                return

    def no_path_selected(self):
        self.status_message = "Choose a specialization path first."

    def specialize_selected_hero(self):
        if self.selected_hero is None:
            self.status_message = "Select a hero first."
            return

        if self.state.guild_upgrades.training_hall_level < 3:
            self.status_message = "Training Hall Lv 3 is required for specialization."
            return

        if not self.selected_path_name:
            self.status_message = "Choose a specialization path first."
            return

        messages = specialize_hero(self.selected_hero, self.selected_path_name)
        self.log_panel.append_lines(messages, auto_scroll=True)
        self.status_message = messages[-1] if messages else "Specialization complete."

        if self.on_save_game:
            self.on_save_game()

    def path_button_rect(self, path_name):
        paths = list(specialization_paths_for_hero(self.selected_hero).keys()) if self.selected_hero else []
        index = paths.index(path_name) if path_name in paths else 0

        width = 420
        height = 108
        gap = 14
        x = self.footer_panel.rect.x + 520 + index * (width + gap)
        y = self.footer_panel.rect.y + 94
        return pygame.Rect(x, y, width, height)

    def next_rank_summary(self, hero, path_name):
        paths = specialization_paths_for_hero(hero)
        path_data = paths.get(path_name, {})
        ranks = list(path_data.get("ranks", []))
        current_rank = int(hero.training_path_progress.get(path_name, 0))

        if current_rank >= len(ranks):
            return "Path mastered."

        stat_block = dict(ranks[current_rank].get("stats", {}))
        if not stat_block:
            return "No stat gain."

        pieces = [f"+{amount} {stat_name}" for stat_name, amount in stat_block.items()]
        return "Next: " + ", ".join(pieces)

    def wrap_lines(self, text, max_width):
        words = str(text).split(" ")
        lines = []
        current = ""

        for word in words:
            trial = word if not current else f"{current} {word}"
            if self.font.size(trial)[0] <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        return lines or [""]