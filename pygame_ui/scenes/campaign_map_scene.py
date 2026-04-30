import pygame

from game_state import campaign_is_active, start_campaign_runtime
from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.ui_helpers import truncate_text, wrap_text
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.key_value_grid import KeyValueGrid
from pygame_ui.widgets.panel import Panel
from pygame_ui.widgets.resource_header import ResourceHeader
from pygame_ui.widgets.scrollable_text_panel import ScrollableTextPanel
from pygame_ui.widgets.status_chip import StatusChip
from systems.campaign.campaign_constants import (
    CAMPAIGN_HOME_BASE_POSITION,
    HERO_STATE_AVAILABLE,
    HERO_STATE_AWAITING_DECISION,
    HERO_STATE_ON_TASK,
    HERO_STATE_RESTING,
    HERO_STATE_RETURNING,
    HERO_STATE_TRAVELING,
    TASK_STATE_ACTIVE,
    TASK_STATE_PENDING,
    TASK_STATE_TRAVELING_TO,
    TASK_STATE_WAITING_FOR_DECISION,
)
from systems.campaign.campaign_runtime import (
    resolve_open_decision,
    tick_campaign_runtime,
)
from systems.campaign.task_dispatch import assign_heroes_to_task, find_task

from ..widgets.button import Button


class CampaignMapScene(SceneBase):
    def __init__(self, state, on_return_to_hub, on_save_game):
        super().__init__()

        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        if not campaign_is_active(self.state):
            start_campaign_runtime(self.state)

        self.runtime = self.state.campaign_runtime
        self.status_message = "Campaign active."

        self.selected_task_id = None
        self.selected_available_hero_index = 0

        self.last_update_ticks = pygame.time.get_ticks()
        self.rng = None

        self.map_rect = pygame.Rect(40, 150, 1180, 760)
        self.sidebar_rect = pygame.Rect(1250, 150, 630, 760)

        self.map_panel = Panel(self.map_rect, "Campaign Map")
        self.sidebar_panel = Panel(self.sidebar_rect, "Campaign Status")

        self.log_panel = ScrollableTextPanel(
            rect=(40, 930, 1840, 90),
            title="Campaign Log",
            font=self.small_font,
            title_font=self.title_font,
            row_spacing=20,
            padding=18,
            title_height=44,
        )

        self.log_panel.set_lines(list(getattr(self.runtime, "event_log", [])))

    def handle_event(self, event):
        if self.log_panel.handle_event(event):
            return

        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", None) == 1:
            if self.handle_task_click(event.pos):
                return

        if self.handle_buttons_click(event, self.build_buttons()):
            return

    def update(self, mouse_pos):
        super().update(mouse_pos)
        self.log_panel.update(mouse_pos)

        now_ticks = pygame.time.get_ticks()
        delta_seconds = max(0.0, (now_ticks - self.last_update_ticks) / 1000.0)
        self.last_update_ticks = now_ticks

        if self.selected_task_id is not None and self.runtime.open_decision_event is None:
            self.runtime.paused = True
        elif self.runtime.open_decision_event is None:
            self.runtime.paused = False

        previous_log_len = len(self.runtime.event_log)
        tick_campaign_runtime(self.runtime, self.state, delta_seconds, self.rng)

        if len(self.runtime.event_log) != previous_log_len:
            self.log_panel.set_lines(list(self.runtime.event_log))
            self.log_panel.scroll_to_bottom()

        if not self.runtime.active:
            self.status_message = "Campaign complete."

    def draw(self, screen):
        self.clear_screen(screen)

        self.draw_header(screen)

        self.map_panel.draw(screen, self.title_font)
        self.sidebar_panel.draw(screen, self.title_font)

        self.draw_map(screen)
        self.draw_sidebar(screen)
        self.draw_modal(screen)

        self.log_panel.draw(screen)
        self.update_and_draw_buttons(screen, self.build_buttons())

    def draw_header(self, screen):
        HeaderPanel(
            rect=(40, 30, 1840, 96),
            title="Campaign Dispatch",
            stats="",
            status_message=self.status_message,
            stats_pos=(60, 70),
            status_pos=(1090, 108),
        ).draw(screen, self.title_font, self.header_font, self.font)

        ResourceHeader(
            resources=[
                ("Gold", f"{self.state.gold}g"),
                ("Time", f"{self.runtime.elapsed_time:.1f}"),
                ("Spawns", f"{self.runtime.total_spawns}/{self.runtime.max_spawns}"),
                ("Tasks", self.live_task_count()),
                ("Heroes Ready", self.available_hero_count()),
            ],
            spacing=180,
            item_max_width=170,
            font_size=24,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=False,
            value_bold=True,
        ).draw(screen, self.font, 60, 72)

    def draw_map(self, screen):
        inner = self.map_inner_rect()
        pygame.draw.rect(screen, (34, 56, 46), inner, border_radius=10)
        pygame.draw.rect(screen, (66, 96, 80), inner, 2, border_radius=10)

        self.draw_home_base(screen)
        self.draw_tasks(screen)
        self.draw_hero_icons(screen)

    def draw_home_base(self, screen):
        home_pos = self.world_to_screen(CAMPAIGN_HOME_BASE_POSITION)
        pygame.draw.circle(screen, (210, 190, 110), home_pos, 18)
        pygame.draw.circle(screen, (245, 230, 150), home_pos, 18, 2)

        label = self.small_font.render("Guild", True, theme.TEXT_PRIMARY)
        screen.blit(label, (home_pos[0] + 20, home_pos[1] - 10))

    def draw_tasks(self, screen):
        for task in self.runtime.active_tasks:
            if task.is_terminal():
                continue

            pos = self.world_to_screen(task.map_position)
            is_selected = task.task_id == self.selected_task_id

            color = (180, 120, 90)
            if task.state == TASK_STATE_PENDING:
                color = (210, 145, 90)
            elif task.state == TASK_STATE_TRAVELING_TO:
                color = (115, 175, 225)
            elif task.state == TASK_STATE_ACTIVE:
                color = (210, 185, 95)
            elif task.state == TASK_STATE_WAITING_FOR_DECISION:
                color = (215, 105, 105)

            radius = 18 if is_selected else 14
            pygame.draw.circle(screen, color, pos, radius)
            pygame.draw.circle(screen, (245, 245, 250), pos, radius, 2)

            task_text = truncate_text(task.task_type, self.small_font, 120)
            screen.blit(
                self.small_font.render(task_text, True, theme.TEXT_PRIMARY),
                (pos[0] + 20, pos[1] - 10),
            )

            self.draw_task_timer_chip(screen, task, pos)

    def draw_task_timer_chip(self, screen, task, pos):
        if task.state == TASK_STATE_PENDING:
            remaining = max(0.0, task.expire_time - self.runtime.elapsed_time)
            chip_text = f"{remaining:.0f}s"
            chip_style = "good"
            if remaining <= 8:
                chip_style = "danger"
            elif remaining <= 14:
                chip_style = "warning"
        elif task.state in (TASK_STATE_ACTIVE, TASK_STATE_WAITING_FOR_DECISION):
            remaining = self.task_completion_time_remaining(task)
            chip_text = f"{remaining:.0f}s"
            chip_style = "warning" if task.state == TASK_STATE_WAITING_FOR_DECISION else "info"
        else:
            return

        StatusChip(
            rect=(pos[0] - 16, pos[1] + 20, 64, 22),
            text=chip_text,
            style=chip_style,
        ).draw(screen, self.small_font)

    def draw_hero_icons(self, screen):
        for hero in self.state.roster:
            hero_state = self.runtime.hero_states.get(hero.name)
            if hero_state is None:
                continue

            position = self.hero_screen_position(hero.name)
            if position is None:
                continue

            color = (180, 220, 180)
            if hero_state.state == HERO_STATE_TRAVELING:
                color = (120, 200, 255)
            elif hero_state.state == HERO_STATE_ON_TASK:
                color = (230, 210, 120)
            elif hero_state.state == HERO_STATE_AWAITING_DECISION:
                color = (235, 145, 145)
            elif hero_state.state == HERO_STATE_RETURNING:
                color = (180, 180, 255)
            elif hero_state.state == HERO_STATE_RESTING:
                color = (140, 140, 150)

            pygame.draw.circle(screen, color, position, 10)
            pygame.draw.circle(screen, (245, 245, 250), position, 10, 1)

            initials = hero.name[:2].upper()
            text = self.small_font.render(initials, True, (20, 20, 24))
            text_rect = text.get_rect(center=position)
            screen.blit(text, text_rect)

    def draw_sidebar(self, screen):
        top_x = self.sidebar_rect.x + 20
        top_y = self.sidebar_rect.y + 50

        KeyValueGrid(
            rows=[
                ("Campaign", "Active" if self.runtime.active else "Complete"),
                ("Paused", "Yes" if self.runtime.paused else "No"),
                ("Elapsed", f"{self.runtime.elapsed_time:.1f}s"),
                ("Remaining Spawns", max(0, self.runtime.max_spawns - self.runtime.total_spawns)),
                ("Live Tasks", self.live_task_count()),
                ("Available Heroes", self.available_hero_count()),
            ],
            columns=1,
            column_width=570,
            row_gap=10,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=True,
            value_bold=False,
            font_size=22,
            line_spacing=2,
        ).draw(
            screen=screen,
            font=self.font,
            x=top_x,
            y=top_y,
        )

        roster_y = top_y + 190
        screen.blit(
            self.font.render("Hero States", True, theme.TEXT_PRIMARY),
            (top_x, roster_y),
        )

        row_y = roster_y + 36
        for hero in self.state.roster[:10]:
            hero_state = self.runtime.hero_states.get(hero.name)
            state_text = hero_state.state if hero_state else "unknown"

            row_rect = pygame.Rect(top_x, row_y, 580, 46)
            pygame.draw.rect(screen, (42, 42, 52), row_rect, border_radius=8)
            pygame.draw.rect(screen, (75, 75, 92), row_rect, 1, border_radius=8)

            left_text = truncate_text(hero.name, self.small_font, 220)
            screen.blit(
                self.small_font.render(left_text, True, theme.TEXT_PRIMARY),
                (row_rect.x + 10, row_rect.y + 7),
            )

            detail_text = self.hero_state_detail_text(hero_state)
            screen.blit(
                self.small_font.render(
                    truncate_text(detail_text, self.small_font, 270),
                    True,
                    theme.TEXT_MUTED,
                ),
                (row_rect.x + 10, row_rect.y + 24),
            )

            StatusChip(
                rect=(row_rect.right - 128, row_rect.y + 11, 110, 22),
                text=state_text.replace("_", " "),
                style=self.hero_state_chip_style(state_text),
            ).draw(screen, self.small_font)

            row_y += 54
            if row_y > self.sidebar_rect.bottom - 30:
                break

    def draw_modal(self, screen):
        if self.runtime.open_decision_event is not None:
            self.draw_decision_modal(screen)
            return

        if self.selected_task_id is not None:
            self.draw_task_modal(screen)

    def draw_task_modal(self, screen):
        task = find_task(self.runtime, self.selected_task_id)
        if task is None:
            return

        modal_rect = pygame.Rect(250, 180, 980, 560)
        pygame.draw.rect(screen, (22, 22, 28), modal_rect, border_radius=14)
        pygame.draw.rect(screen, (120, 120, 145), modal_rect, 2, border_radius=14)

        title = self.title_font.render("Task Inspection", True, theme.TEXT_PRIMARY)
        screen.blit(title, (modal_rect.x + 24, modal_rect.y + 18))

        time_label, time_value = self.task_time_label_and_value(task)

        KeyValueGrid(
            rows=[
                ("Task", task.task_type),
                ("State", task.state),
                ("Recommended Power", task.recommended_power),
                ("Travel Time", f"{task.travel_time:.1f}s"),
                ("Task Duration", f"{task.task_duration:.1f}s"),
                ("Reward", f"{task.reward_gold_min}-{task.reward_gold_max}g / {task.reward_xp} XP"),
                ("Preferred Classes", ", ".join(task.preferred_classes) or "Any"),
                ("Assigned Heroes", ", ".join(task.assigned_heroes) or "None"),
                (time_label, time_value),
            ],
            columns=1,
            column_width=440,
            row_gap=10,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=True,
            value_bold=False,
            font_size=22,
            line_spacing=2,
        ).draw(
            screen=screen,
            font=self.font,
            x=modal_rect.x + 24,
            y=modal_rect.y + 64,
        )

        available_heroes = self.available_heroes()
        selected_hero_name = "None"
        if available_heroes:
            self.selected_available_hero_index = max(
                0,
                min(self.selected_available_hero_index, len(available_heroes) - 1),
            )
            selected_hero_name = available_heroes[self.selected_available_hero_index].name

        right_x = modal_rect.x + 520
        right_y = modal_rect.y + 64

        screen.blit(
            self.font.render("Dispatch Selection", True, theme.TEXT_PRIMARY),
            (right_x, right_y),
        )

        arrival_window = "Locked"
        if task.state == TASK_STATE_PENDING:
            arrival_window = "On time" if self.runtime.elapsed_time + task.travel_time <= task.expire_time else "Too late"
        elif task.assigned_heroes:
            arrival_window = "Already assigned"

        next_milestone = "Assign hero to start travel"
        if task.state == TASK_STATE_PENDING:
            next_milestone = f"Expires in {max(0.0, task.expire_time - self.runtime.elapsed_time):.1f}s"
        elif task.state == TASK_STATE_TRAVELING_TO:
            next_milestone = "Hero is traveling"
        elif task.state in (TASK_STATE_ACTIVE, TASK_STATE_WAITING_FOR_DECISION):
            next_milestone = f"Completes in {self.task_completion_time_remaining(task):.1f}s"

        KeyValueGrid(
            rows=[
                ("Selected Hero", selected_hero_name),
                ("Available Pool", len(available_heroes)),
                ("Arrival Window", arrival_window),
                ("Next Milestone", next_milestone),
            ],
            columns=1,
            column_width=400,
            row_gap=10,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=True,
            value_bold=False,
            font_size=22,
            line_spacing=2,
        ).draw(
            screen=screen,
            font=self.font,
            x=right_x,
            y=right_y + 40,
        )

        help_lines = [
            "Inspecting a task pauses campaign time.",
            "Travel uses visible movement instead of a countdown.",
            "Rest time is shown only in the hero states panel.",
        ]
        help_y = right_y + 210
        for line in help_lines:
            wrapped = wrap_text(line, self.small_font, 390)
            for wrapped_line in wrapped:
                screen.blit(
                    self.small_font.render(wrapped_line, True, theme.TEXT_SECONDARY),
                    (right_x, help_y),
                )
                help_y += 18
            help_y += 8

    def draw_decision_modal(self, screen):
        event = self.runtime.open_decision_event
        if event is None:
            return

        modal_rect = pygame.Rect(360, 220, 860, 420)
        pygame.draw.rect(screen, (24, 22, 28), modal_rect, border_radius=14)
        pygame.draw.rect(screen, (150, 115, 115), modal_rect, 2, border_radius=14)

        screen.blit(
            self.title_font.render(event.title, True, theme.TEXT_PRIMARY),
            (modal_rect.x + 24, modal_rect.y + 20),
        )

        wrapped_desc = wrap_text(event.description, self.font, modal_rect.width - 48)
        y = modal_rect.y + 70
        for line in wrapped_desc:
            screen.blit(
                self.font.render(line, True, theme.TEXT_SECONDARY),
                (modal_rect.x + 24, y),
            )
            y += 24

        y += 18
        for index, choice in enumerate(event.choices):
            row_rect = pygame.Rect(modal_rect.x + 24, y, modal_rect.width - 48, 52)
            pygame.draw.rect(screen, (44, 44, 54), row_rect, border_radius=10)
            pygame.draw.rect(screen, (90, 90, 110), row_rect, 1, border_radius=10)

            label = f"{index + 1}. {choice.get('label', 'Choice')}"
            screen.blit(
                self.font.render(label, True, theme.TEXT_PRIMARY),
                (row_rect.x + 14, row_rect.y + 14),
            )
            y += 64

    def build_buttons(self):
        buttons = [
            Button((1660, 72, 180, 36), "Return to Hub", self.return_to_hub),
        ]

        if self.selected_task_id is not None and self.runtime.open_decision_event is None:
            buttons.append(Button((995, 680, 140, 38), "Close", self.close_task_modal))
            buttons.append(Button((820, 680, 140, 38), "Prev Hero", self.select_prev_hero))
            buttons.append(Button((645, 680, 140, 38), "Next Hero", self.select_next_hero))
            buttons.append(Button((470, 680, 140, 38), "Assign", self.assign_selected_hero))

        if self.runtime.open_decision_event is not None:
            event = self.runtime.open_decision_event
            button_y = 560
            button_x = 430
            for choice in event.choices:
                choice_id = choice.get("id", "")
                label = choice.get("label", "Choose")
                buttons.append(
                    Button(
                        (button_x, button_y, 220, 42),
                        label,
                        lambda cid=choice_id: self.resolve_decision(cid),
                    )
                )
                button_x += 240

        return buttons

    def handle_task_click(self, pos):
        for task in self.runtime.active_tasks:
            if task.is_terminal():
                continue

            icon_center = self.world_to_screen(task.map_position)
            icon_rect = pygame.Rect(icon_center[0] - 22, icon_center[1] - 22, 44, 44)
            label_rect = pygame.Rect(icon_center[0] + 16, icon_center[1] - 18, 130, 28)
            chip_rect = pygame.Rect(icon_center[0] - 18, icon_center[1] + 18, 72, 28)

            if icon_rect.collidepoint(pos) or label_rect.collidepoint(pos) or chip_rect.collidepoint(pos):
                self.selected_task_id = task.task_id
                self.runtime.paused = True
                self.status_message = f"Inspecting {task.task_type}."
                return True

        return False

    def assign_selected_hero(self):
        if self.selected_task_id is None:
            self.status_message = "No task selected."
            return

        task = find_task(self.runtime, self.selected_task_id)
        if task is None:
            self.status_message = "Task not found."
            return

        if task.state != TASK_STATE_PENDING:
            self.status_message = "This task is no longer waiting for assignment."
            return

        available = self.available_heroes()
        if not available:
            self.status_message = "No available heroes."
            return

        self.selected_available_hero_index = max(
            0,
            min(self.selected_available_hero_index, len(available) - 1),
        )
        hero = available[self.selected_available_hero_index]

        success, message = assign_heroes_to_task(
            runtime=self.runtime,
            hero_names=[hero.name],
            task_id=self.selected_task_id,
            now=self.runtime.elapsed_time,
        )

        self.log_panel.set_lines(list(self.runtime.event_log))
        self.log_panel.scroll_to_bottom()

        if success:
            self.status_message = f"{hero.name} dispatched."
            self.selected_task_id = None
            self.runtime.paused = False
            if self.on_save_game:
                self.on_save_game()
        else:
            self.status_message = message

    def select_prev_hero(self):
        available = self.available_heroes()
        if not available:
            return
        self.selected_available_hero_index = (self.selected_available_hero_index - 1) % len(available)

    def select_next_hero(self):
        available = self.available_heroes()
        if not available:
            return
        self.selected_available_hero_index = (self.selected_available_hero_index + 1) % len(available)

    def close_task_modal(self):
        self.selected_task_id = None
        if self.runtime.open_decision_event is None:
            self.runtime.paused = False
        self.status_message = "Campaign resumed."

    def resolve_decision(self, choice_id):
        self.status_message = resolve_open_decision(self.runtime, choice_id)
        self.log_panel.set_lines(list(self.runtime.event_log))
        self.log_panel.scroll_to_bottom()
        if self.on_save_game:
            self.on_save_game()

    def return_to_hub(self):
        if self.on_save_game:
            self.on_save_game()
        self.on_return_to_hub("Returned from campaign.")

    def available_heroes(self):
        available = []
        for hero in self.state.roster:
            hero_state = self.runtime.hero_states.get(hero.name)
            if hero_state is not None and hero_state.state == HERO_STATE_AVAILABLE:
                available.append(hero)
        return available

    def available_hero_count(self):
        return len(self.available_heroes())

    def live_task_count(self):
        return sum(1 for task in self.runtime.active_tasks if not task.is_terminal())

    def map_inner_rect(self):
        return pygame.Rect(
            self.map_rect.x + 18,
            self.map_rect.y + 42,
            self.map_rect.width - 36,
            self.map_rect.height - 60,
        )

    def world_to_screen(self, position):
        inner = self.map_inner_rect()
        map_x, map_y = position
        return (
            inner.x + int((map_x / 1600.0) * inner.width),
            inner.y + int((map_y / 900.0) * inner.height),
        )

    def hero_screen_position(self, hero_name):
        hero_state = self.runtime.hero_states.get(hero_name)
        if hero_state is None:
            return None

        if hero_state.state in (HERO_STATE_AVAILABLE, HERO_STATE_RESTING):
            return self.world_to_screen(CAMPAIGN_HOME_BASE_POSITION)

        task = find_task(self.runtime, hero_state.assigned_task_id) if hero_state.assigned_task_id else None
        if task is None:
            return self.world_to_screen(CAMPAIGN_HOME_BASE_POSITION)

        home = CAMPAIGN_HOME_BASE_POSITION
        target = task.map_position

        if hero_state.state == HERO_STATE_TRAVELING:
            if hero_state.travel_end_time is None:
                return self.world_to_screen(home)

            start_time = hero_state.travel_end_time - task.travel_time
            progress = self.progress_between(start_time, hero_state.travel_end_time, self.runtime.elapsed_time)
            return self.world_to_screen(self.lerp_position(home, target, progress))

        if hero_state.state in (HERO_STATE_ON_TASK, HERO_STATE_AWAITING_DECISION):
            return self.world_to_screen(target)

        if hero_state.state == HERO_STATE_RETURNING:
            if hero_state.return_end_time is None:
                return self.world_to_screen(target)

            start_time = hero_state.return_end_time - task.travel_time
            progress = self.progress_between(start_time, hero_state.return_end_time, self.runtime.elapsed_time)
            return self.world_to_screen(self.lerp_position(target, home, progress))

        return self.world_to_screen(home)

    def progress_between(self, start_time, end_time, now):
        duration = max(0.001, end_time - start_time)
        return max(0.0, min(1.0, (now - start_time) / duration))

    def lerp_position(self, start_pos, end_pos, t):
        sx, sy = start_pos
        ex, ey = end_pos
        return (
            int(sx + ((ex - sx) * t)),
            int(sy + ((ey - sy) * t)),
        )

    def hero_state_chip_style(self, state_text):
        if state_text == HERO_STATE_AVAILABLE:
            return "good"
        if state_text == HERO_STATE_TRAVELING:
            return "info"
        if state_text in (HERO_STATE_ON_TASK, HERO_STATE_RETURNING):
            return "warning"
        if state_text == HERO_STATE_AWAITING_DECISION:
            return "danger"
        if state_text == HERO_STATE_RESTING:
            return "default"
        return "default"

    def hero_state_detail_text(self, hero_state):
        if hero_state is None:
            return "No runtime state"

        if hero_state.state == HERO_STATE_RESTING and hero_state.rest_end_time is not None:
            remaining = max(0.0, hero_state.rest_end_time - self.runtime.elapsed_time)
            return f"Resting {remaining:.0f}s"

        if hero_state.state == HERO_STATE_TRAVELING:
            return "Traveling to task"

        if hero_state.state == HERO_STATE_ON_TASK:
            task = find_task(self.runtime, hero_state.assigned_task_id) if hero_state.assigned_task_id else None
            if task is not None:
                remaining = max(0.0, self.task_completion_time_remaining(task))
                return f"Working {remaining:.0f}s"
            return "Working"

        if hero_state.state == HERO_STATE_AWAITING_DECISION:
            return "Awaiting decision"

        if hero_state.state == HERO_STATE_RETURNING:
            return "Returning to guild"

        return "Ready"

    def task_completion_time_remaining(self, task):
        if task.state not in (TASK_STATE_ACTIVE, TASK_STATE_WAITING_FOR_DECISION):
            return 0.0

        if task.active_until is None:
            return task.task_duration if task.state == TASK_STATE_WAITING_FOR_DECISION else 0.0

        return max(0.0, task.active_until - self.runtime.elapsed_time)

    def task_time_label_and_value(self, task):
        if task.state == TASK_STATE_PENDING:
            return ("Expires In", f"{max(0.0, task.expire_time - self.runtime.elapsed_time):.1f}s")

        if task.state == TASK_STATE_TRAVELING_TO:
            return ("Travel", "Hero en route")

        if task.state in (TASK_STATE_ACTIVE, TASK_STATE_WAITING_FOR_DECISION):
            return ("Completion In", f"{self.task_completion_time_remaining(task):.1f}s")

        return ("Time", "N/A")