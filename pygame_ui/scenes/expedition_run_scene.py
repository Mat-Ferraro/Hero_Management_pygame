import pygame

from event_system import choose_event_for_enemy
from expedition_runner import finish_expedition
from manager_reputation import reputation_for_level_up
from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.ui_helpers import truncate_text, wrap_text
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.key_value_grid import KeyValueGrid
from pygame_ui.widgets.panel import Panel
from pygame_ui.widgets.row_styles import draw_selectable_row
from pygame_ui.widgets.scrollable_text_panel import ScrollableTextPanel
from pygame_ui.widgets.status_chip import StatusChip
from systems.campaign_cycle import CampaignCycleManager
from systems.combat_system import estimate_success_chance
from systems.mentorship_system import apply_party_mentorship
from systems.room_system import (
    COMBAT_ROOM_TYPES,
    generate_room_options,
    resolve_event_choice,
    resolve_room,
)
from systems.survivor_system import remove_temporary_survivors_from_party

from ..widgets.button import Button


class ExpeditionRunScene(SceneBase):
    CHOICE_ROW_HEIGHT = 82
    CHOICE_ROW_SPACING = 94

    EVENT_ROW_HEIGHT = 54
    EVENT_ROW_SPACING = 66
    EVENT_FIRST_ROW_Y = 304

    PARTY_ROW_HEIGHT = 42
    PARTY_ROW_SPACING = 10

    def __init__(self, state, party, dungeon, on_return_to_hub, on_save_game):
        super().__init__()

        self.state = state
        self.party = party
        self.dispatched_heroes = list(party)
        self.dungeon = dungeon
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        self.status_message = "Choose the next room."

        self.room_number = 1
        self.rooms_completed = 0
        self.loot_earned = 0
        self.xp_earned = 0

        self.room_options = []

        self.awaiting_continue = False
        self.awaiting_event_choice = False
        self.expedition_finished = False

        self.active_event = None
        self.active_event_room_option = None

        self.choice_panel_rect = pygame.Rect(40, 150, 760, 540)
        self.party_panel_rect = pygame.Rect(840, 150, 1040, 360)
        self.details_panel_rect = pygame.Rect(840, 530, 1040, 160)

        self.choice_panel = Panel(self.choice_panel_rect, "Choose Path")
        self.party_panel = Panel(self.party_panel_rect, "Party Status")
        self.details_panel = Panel(self.details_panel_rect, "Run Details")

        self.log_panel = ScrollableTextPanel(
            rect=(40, 730, 1840, 290),
            title="Expedition Log",
            font=self.font,
            title_font=self.title_font,
            row_spacing=22,
            padding=20,
            title_height=54,
        )

        self.log_lines = self.log_panel.lines
        self.party_scroll = 0

        for hero in self.party:
            hero.reset_health_for_expedition()
            hero.participated_this_cycle = True

        self.log_panel.append_lines([f"Expedition started: {self.dungeon.name}"], auto_scroll=True)
        self.generate_next_room_options()

    def handle_event(self, event):
        if self.log_panel.handle_event(event):
            return

        if self.handle_party_scroll(event):
            return

        if self.handle_buttons_click(event, self.build_buttons()):
            return

        if self.is_left_click(event):
            if self.handle_choice_click(event.pos):
                return

    def update(self, mouse_pos):
        super().update(mouse_pos)
        self.log_panel.update(mouse_pos)

    def draw(self, screen):
        self.clear_screen(screen)

        self.draw_header(screen)

        self.choice_panel.draw(screen, self.title_font)
        self.party_panel.draw(screen, self.title_font)
        self.details_panel.draw(screen, self.title_font)

        self.draw_choices(screen)
        self.draw_party(screen)
        self.draw_run_details(screen)
        self.log_panel.draw(screen)

        self.update_and_draw_buttons(screen, self.build_buttons())

    def draw_header(self, screen):
        HeaderPanel(
            rect=(40, 30, 1840, 96),
            title="Expedition Run",
            stats="",
            status_message=self.status_message,
            stats_pos=(60, 74),
            status_pos=(1060, 112),
        ).draw(screen, self.title_font, self.header_font, self.font)

        from pygame_ui.widgets.resource_header import ResourceHeader
        ResourceHeader(
            resources=[
                ("Gold", f"{self.state.gold}g"),
                ("Year", self.state.year),
                ("Room", f"{min(self.room_number, self.dungeon.room_count)}/{self.dungeon.room_count}"),
                ("Loot", f"{self.loot_earned}g"),
                ("XP", self.xp_earned),
            ],
            spacing=190,
            item_max_width=180,
            font_size=24,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=False,
            value_bold=True,
        ).draw(screen, self.font, 60, 72)

    def draw_choices(self, screen):
        if self.expedition_finished:
            self.draw_choice_message(
                screen,
                "The expedition is finished. Review the results, then return to the guild hall.",
            )
            return

        if self.awaiting_event_choice:
            self.draw_event_choices(screen)
            return

        if self.awaiting_continue:
            self.draw_choice_message(
                screen,
                "Room resolved. Continue deeper into the dungeon, or retreat now.",
            )
            return

        y = 210
        for index, option in enumerate(self.room_options, start=1):
            row_rect = self.choice_row_rect(y)
            is_hovered = row_rect.collidepoint(self.mouse_pos)

            draw_selectable_row(
                screen,
                row_rect,
                False,
                is_hovered,
                style="dark",
            )

            title = f"{index}. {option.room_type}"
            screen.blit(
                self.font.render(title, True, theme.TEXT_PRIMARY),
                (row_rect.x + 14, row_rect.y + 8),
            )

            text_width = row_rect.width - 120
            wrapped_desc = wrap_text(option.description, self.small_font, text_width)
            desc_y = row_rect.y + 34
            for line in wrapped_desc[:2]:
                screen.blit(
                    self.small_font.render(line, True, theme.TEXT_SECONDARY),
                    (row_rect.x + 14, desc_y),
                )
                desc_y += 18

            if option.room_type in COMBAT_ROOM_TYPES:
                enemy_power = self.dungeon.room_enemy_power(self.room_number, option.room_type)
                enemy_type = self.dungeon.enemy_type_for_room(option.room_type)
                chance = estimate_success_chance(self.party, enemy_power, option.room_type, enemy_type)

                info_text = f"Enemy Power {enemy_power} | Type {enemy_type}"
                screen.blit(
                    self.small_font.render(info_text, True, theme.TEXT_MUTED),
                    (row_rect.x + 14, row_rect.bottom - 22),
                )

                chance_percent = int(round(chance * 100))
                chip_style = "danger"
                if chance >= 0.65:
                    chip_style = "good"
                elif chance >= 0.40:
                    chip_style = "warning"

                StatusChip(
                    rect=(row_rect.right - 96, row_rect.y + 10, 76, 22),
                    text=f"{chance_percent}%",
                    style=chip_style,
                ).draw(screen, self.small_font)

            y += self.CHOICE_ROW_SPACING

    def draw_event_choices(self, screen):
        if not self.active_event:
            self.draw_choice_message(screen, "No event loaded.")
            return

        name = self.active_event.get("name", "Unknown Event")
        description = self.active_event.get("description", "")

        screen.blit(
            self.font.render(f"Event: {name}", True, (235, 220, 180)),
            (60, 206),
        )

        wrapped_description = wrap_text(description, self.small_font, 650)
        y = 238
        for line in wrapped_description[:3]:
            screen.blit(
                self.small_font.render(line, True, theme.TEXT_SECONDARY),
                (60, y),
            )
            y += 18

        y += 12
        for index, choice in enumerate(self.active_event.get("choices", []), start=1):
            row_rect = self.event_choice_row_rect(y)
            draw_selectable_row(
                screen,
                row_rect,
                False,
                row_rect.collidepoint(self.mouse_pos),
                style="dark",
            )

            choice_label = choice.get("label", "Unknown choice")
            wrapped = wrap_text(f"{index}. {choice_label}", self.small_font, row_rect.width - 24)

            line_y = row_rect.y + 10
            for line in wrapped[:2]:
                screen.blit(
                    self.small_font.render(line, True, theme.TEXT_SECONDARY),
                    (row_rect.x + 12, line_y),
                )
                line_y += 18

            y += self.EVENT_ROW_SPACING

    def draw_choice_message(self, screen, message):
        wrapped = wrap_text(message, self.font, 660)
        y = 220

        for line in wrapped:
            screen.blit(
                self.font.render(line, True, theme.TEXT_SECONDARY),
                (60, y),
            )
            y += 26

    def draw_party(self, screen):
        summary_title_x = self.party_panel_rect.x + 24
        summary_y = self.party_panel_rect.y + 52

        displayed_party = self.displayed_party()

        screen.blit(
            self.font.render("Party Summary", True, theme.TEXT_PRIMARY),
            (summary_title_x, summary_y),
        )

        summary_line = (
            f"Heroes {len(displayed_party)}    "
            f"Power {self.displayed_party_power()}    "
            f"Mentor {self.displayed_party_mentor_count()}    "
            f"Cost {self.displayed_party_cost()}g"
        )
        screen.blit(
            self.small_font.render(summary_line, True, theme.TEXT_SECONDARY),
            (summary_title_x, summary_y + 30),
        )

        content_rect = self.party_content_rect()

        if not displayed_party:
            screen.blit(
                self.font.render("No heroes remain.", True, (220, 120, 120)),
                (content_rect.x, content_rect.y + 8),
            )
            return

        visible_rows = self.party_visible_rows()
        max_scroll = max(0, len(displayed_party) - visible_rows)
        self.party_scroll = max(0, min(self.party_scroll, max_scroll))

        visible_party = displayed_party[self.party_scroll : self.party_scroll + visible_rows]

        row_y = content_rect.y
        for hero in visible_party:
            row_rect = pygame.Rect(
                content_rect.x,
                row_y,
                content_rect.width - 26,
                self.PARTY_ROW_HEIGHT,
            )

            status = hero.health_status()
            chip_style = "good"
            status_text = "Healthy"
            text_color = theme.TEXT_PRIMARY

            if status == "DEAD":
                pygame.draw.rect(screen, (12, 12, 14), row_rect, border_radius=8)
                pygame.draw.rect(screen, (150, 30, 30), row_rect, 2, border_radius=8)
                chip_style = "danger"
                status_text = "Dead"
                text_color = (215, 215, 215)
            elif status == "CRITICAL":
                pygame.draw.rect(screen, (28, 18, 18), row_rect, border_radius=8)
                pygame.draw.rect(screen, (190, 110, 40), row_rect, 2, border_radius=8)
                chip_style = "warning"
                status_text = "Critical"
                text_color = (235, 210, 180)
            elif status in ("WOUNDED", "HURT"):
                draw_selectable_row(
                    screen,
                    row_rect,
                    False,
                    row_rect.collidepoint(self.mouse_pos),
                    style="brown",
                )
                chip_style = "warning"
                status_text = "Hurt" if status == "HURT" else "Wounded"
                text_color = (235, 220, 180)
            elif getattr(hero, "is_temporary_survivor", False):
                draw_selectable_row(
                    screen,
                    row_rect,
                    False,
                    row_rect.collidepoint(self.mouse_pos),
                    style="dark",
                )
                chip_style = "info"
                status_text = "Survivor"
                text_color = (210, 225, 245)
            else:
                draw_selectable_row(
                    screen,
                    row_rect,
                    False,
                    row_rect.collidepoint(self.mouse_pos),
                    style="green",
                )

            hp_text = "Ready"
            if hero.current_health is not None:
                hp_text = f"{hero.current_health}/{hero.max_health()} HP"

            line = (
                f"{hero.name} | {hero.hero_class} | {hero.career_stage()} | "
                f"Lv {hero.level} | Pwr {hero.combat_power()} | {hp_text} | "
                f"Mentor {hero.mentorship_value()}"
            )

            rendered = truncate_text(line, self.small_font, row_rect.width - 110)
            screen.blit(
                self.small_font.render(rendered, True, text_color),
                (row_rect.x + 10, row_rect.y + 11),
            )

            StatusChip(
                rect=(row_rect.right - 84, row_rect.y + 10, 72, 22),
                text=status_text,
                style=chip_style,
            ).draw(screen, self.small_font)

            row_y += self.PARTY_ROW_HEIGHT + self.PARTY_ROW_SPACING

        self.draw_party_scrollbar(screen, content_rect, visible_rows, len(displayed_party))

    def draw_party_scrollbar(self, screen, content_rect, visible_rows, total_rows):
        if total_rows <= visible_rows:
            return

        track_rect = pygame.Rect(
            content_rect.right - 14,
            content_rect.y,
            8,
            content_rect.height,
        )

        pygame.draw.rect(screen, (58, 58, 70), track_rect, border_radius=4)

        thumb_height = max(40, int(track_rect.height * (visible_rows / total_rows)))
        max_scroll = max(1, total_rows - visible_rows)
        scroll_ratio = self.party_scroll / max_scroll
        thumb_y = track_rect.y + int((track_rect.height - thumb_height) * scroll_ratio)

        thumb_rect = pygame.Rect(
            track_rect.x,
            thumb_y,
            track_rect.width,
            thumb_height,
        )
        pygame.draw.rect(screen, (130, 130, 150), thumb_rect, border_radius=4)

    def draw_run_details(self, screen):
        left_x = self.details_panel_rect.x + 24
        middle_x = self.details_panel_rect.x + 320
        right_x = self.details_panel_rect.x + 650
        top_y = self.details_panel_rect.y + 50

        progress_width = 280
        progress_height = 14
        progress = 0
        if self.dungeon.room_count > 0:
            progress = self.rooms_completed / self.dungeon.room_count

        pygame.draw.rect(
            screen,
            (90, 82, 110),
            (left_x, top_y - 6, progress_width, progress_height),
            border_radius=7,
        )
        pygame.draw.rect(
            screen,
            (232, 187, 107),
            (left_x, top_y - 6, int(progress_width * progress), progress_height),
            border_radius=7,
        )

        focused = ", ".join(hero.name for hero in self.displayed_party()) if self.displayed_party() else "None"

        KeyValueGrid(
            rows=[
                ("Dungeon", self.dungeon.name),
                ("Rooms Cleared", f"{self.rooms_completed}/{self.dungeon.room_count}"),
                ("Recovered Loot", f"{self.loot_earned}g"),
            ],
            columns=1,
            column_width=250,
            row_gap=8,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=True,
            value_bold=False,
            font_size=20,
            line_spacing=2,
        ).draw(screen, self.font, left_x, top_y + 24)

        KeyValueGrid(
            rows=[
                ("State", self.current_state_text()),
                ("Enemy Type", self.dungeon.enemy_type),
                ("Recovered XP", self.xp_earned),
            ],
            columns=1,
            column_width=260,
            row_gap=8,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=True,
            value_bold=False,
            font_size=20,
            line_spacing=2,
        ).draw(screen, self.font, middle_x, top_y + 24)

        KeyValueGrid(
            rows=[
                ("Focused Heroes", focused),
                ("Notes", "Review the log to track all room outcomes."),
            ],
            columns=1,
            column_width=300,
            row_gap=8,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=True,
            value_bold=False,
            font_size=20,
            line_spacing=2,
        ).draw(screen, self.font, right_x, top_y + 24)

    def build_buttons(self):
        buttons = []
        panel_padding = 22
        button_height = 38

        if self.expedition_finished:
            return_width = 150
            button_y = self.choice_panel_rect.bottom - panel_padding - button_height
            button_x = self.choice_panel_rect.right - panel_padding - return_width

            buttons.append(
                Button(
                    (button_x, button_y, return_width, button_height),
                    "Return to Hub",
                    self.return_to_hub,
                )
            )
            return buttons

        if self.awaiting_continue:
            gap = 14
            retreat_width = 120
            continue_width = 130

            button_y = self.choice_panel_rect.bottom - panel_padding - button_height
            continue_x = self.choice_panel_rect.right - panel_padding - continue_width
            retreat_x = continue_x - gap - retreat_width

            buttons.append(
                Button(
                    (retreat_x, button_y, retreat_width, button_height),
                    "Retreat",
                    self.retreat,
                )
            )
            buttons.append(
                Button(
                    (continue_x, button_y, continue_width, button_height),
                    "Continue",
                    self.continue_to_next_room,
                )
            )
            return buttons

        return buttons

    def handle_choice_click(self, pos):
        if self.expedition_finished or self.awaiting_continue:
            return False

        if self.awaiting_event_choice:
            y = self.EVENT_FIRST_ROW_Y
            for choice in self.active_event.get("choices", []):
                row_rect = self.event_choice_row_rect(y)
                if row_rect.collidepoint(pos):
                    self.resolve_event_choice_button(choice)
                    return True
                y += self.EVENT_ROW_SPACING
            return False

        y = 210
        for option in self.room_options:
            row_rect = self.choice_row_rect(y)
            if row_rect.collidepoint(pos):
                self.resolve_room_choice(option)
                return True
            y += self.CHOICE_ROW_SPACING

        return False

    def handle_party_scroll(self, event):
        displayed_party = self.displayed_party()
        visible_rows = self.party_visible_rows()
        max_scroll = max(0, len(displayed_party) - visible_rows)
        if max_scroll <= 0:
            return False

        if event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            if self.party_panel_rect.collidepoint(mouse_pos):
                self.party_scroll = max(0, min(self.party_scroll - event.y, max_scroll))
                return True

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4 and self.party_panel_rect.collidepoint(event.pos):
                self.party_scroll = max(0, self.party_scroll - 1)
                return True
            if event.button == 5 and self.party_panel_rect.collidepoint(event.pos):
                self.party_scroll = min(max_scroll, self.party_scroll + 1)
                return True

        return False

    def party_content_rect(self):
        return pygame.Rect(
            self.party_panel_rect.x + 20,
            self.party_panel_rect.y + 112,
            self.party_panel_rect.width - 40,
            self.party_panel_rect.height - 132,
        )

    def party_visible_rows(self):
        content_rect = self.party_content_rect()
        row_space = self.PARTY_ROW_HEIGHT + self.PARTY_ROW_SPACING
        return max(1, content_rect.height // row_space)

    def displayed_party(self):
        displayed = list(self.dispatched_heroes)

        for hero in self.party:
            if hero not in displayed:
                displayed.append(hero)

        return displayed

    def displayed_party_power(self):
        return sum(hero.combat_power() for hero in self.displayed_party())

    def displayed_party_cost(self):
        return sum(getattr(hero, "wage_per_year", 0) for hero in self.displayed_party())

    def displayed_party_mentor_count(self):
        return sum(hero.mentorship_value() for hero in self.displayed_party())

    def generate_next_room_options(self):
        self.room_options = generate_room_options(self.dungeon, self.room_number)

    def resolve_room_choice(self, room_option):
        if room_option.room_type == "Event":
            self.active_event = choose_event_for_enemy(self.dungeon.enemy_type)
            self.active_event_room_option = room_option
            self.awaiting_event_choice = True
            self.status_message = "Choose an event response."
            return

        room_messages = [
            f"=== Room {self.room_number}: {room_option.room_type} ===",
            room_option.description,
        ]

        resolution = resolve_room(
            state=self.state,
            party=self.party,
            dungeon=self.dungeon,
            room_number=self.room_number,
            room_option=room_option,
        )

        self.apply_room_resolution(room_messages, resolution)

    def resolve_event_choice_button(self, choice):
        if not self.active_event or not self.active_event_room_option:
            self.status_message = "Event failed to resolve."
            return

        room_messages = [
            f"=== Room {self.room_number}: Event ===",
            self.active_event_room_option.description,
        ]

        resolution = resolve_event_choice(
            state=self.state,
            party=self.party,
            dungeon=self.dungeon,
            event=self.active_event,
            choice=choice,
        )

        self.awaiting_event_choice = False
        self.active_event = None
        self.active_event_room_option = None

        self.apply_room_resolution(room_messages, resolution)

    def apply_room_resolution(self, room_messages, resolution):
        room_messages.extend(resolution.messages)
        self.rooms_completed += 1

        if resolution.party_wiped:
            room_messages.append("Room rewards were not recovered because no heroes escaped.")
        else:
            self.loot_earned += resolution.loot
            self.xp_earned += resolution.xp
            self.state.gold += resolution.loot

            if resolution.loot > 0:
                room_messages.append(f"Gold after recovered room loot: {self.state.gold}g.")

        self.log_panel.append_lines(room_messages, auto_scroll=True)

        if not self.party:
            self.log_panel.append_lines(
                ["The expedition ends because the entire party is gone."],
                auto_scroll=True,
            )
            self.finish_expedition_run(completed=False)
            return

        if self.rooms_completed >= self.dungeon.room_count:
            self.finish_expedition_run(completed=True)
            return

        self.awaiting_continue = True
        self.status_message = "Room resolved."

    def continue_to_next_room(self):
        self.room_number += 1
        self.awaiting_continue = False
        self.status_message = "Choose the next room."
        self.generate_next_room_options()

    def retreat(self):
        self.log_panel.append_lines(
            [f"The party retreats after completing {self.rooms_completed} room(s)."],
            auto_scroll=True,
        )
        self.finish_expedition_run(completed=False)

    def finish_expedition_run(self, completed):
        self.expedition_finished = True
        self.awaiting_continue = False
        self.awaiting_event_choice = False

        end_messages = [
            f"Total recovered expedition loot: {self.loot_earned}g.",
            f"Total recovered combat XP: {self.xp_earned}.",
        ]

        if completed and self.party:
            end_messages.append("The dungeon route was completed!")

        self.apply_xp_and_cleanup(end_messages)
        self.apply_mentorship(end_messages)

        cycle_manager = CampaignCycleManager(self.state)
        end_messages.extend(cycle_manager.advance_cycle(self.dispatched_heroes))
        end_messages.extend(finish_expedition(self.state, self.dungeon))

        self.log_panel.append_lines(end_messages, auto_scroll=True)

        if self.on_save_game is not None:
            self.on_save_game()

        self.status_message = "Expedition complete. Review the results and return to the hub."

    def apply_xp_and_cleanup(self, messages):
        for hero in list(self.party):
            if hero.is_temporary_survivor:
                continue

            old_level = hero.level
            xp_messages = hero.add_xp(self.xp_earned)
            messages.extend(xp_messages)

            if hero.level > old_level:
                for _ in range(hero.level - old_level):
                    messages.extend(reputation_for_level_up(self.state.reputation, hero.hero_class))

        messages.extend(remove_temporary_survivors_from_party(self.state, self.party))

    def apply_mentorship(self, messages):
        mentorship_messages = apply_party_mentorship(self.party, self.xp_earned)
        if mentorship_messages:
            messages.append("=== Mentorship ===")
            messages.extend(mentorship_messages)

    def current_state_text(self):
        if self.expedition_finished:
            return "Expedition finished"
        if self.awaiting_event_choice:
            return "Awaiting event choice"
        if self.awaiting_continue:
            return "Room resolved"
        return "Awaiting room choice"

    def return_to_hub(self):
        self.on_return_to_hub("Returned from expedition.")

    def choice_row_rect(self, y):
        return pygame.Rect(56, y, 720, self.CHOICE_ROW_HEIGHT)

    def event_choice_row_rect(self, y):
        return pygame.Rect(56, y, 720, self.EVENT_ROW_HEIGHT)