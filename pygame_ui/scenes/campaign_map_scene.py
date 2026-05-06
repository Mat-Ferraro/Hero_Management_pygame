import pygame

from game_state import campaign_is_active, start_campaign_runtime
from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.ui_helpers import truncate_text
from pygame_ui.widgets.button import Button
from pygame_ui.widgets.header_panel import HeaderPanel
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
    TASK_STATE_AWAITING_ACK,
    TASK_STATE_PENDING,
    TASK_STATE_TRAVELING_TO,
    TASK_STATE_WAITING_FOR_DECISION,
)
from systems.campaign.campaign_runtime import tick_campaign_runtime
from systems.campaign.task_dispatch import find_task


class CampaignMapScene(SceneBase):
    def __init__(
        self,
        state,
        on_campaign_complete,
        on_open_task,
        on_save_game,
        status_message="",
    ):
        super().__init__()

        self.state = state
        self.on_campaign_complete = on_campaign_complete
        self.on_open_task = on_open_task
        self.on_save_game = on_save_game

        if not campaign_is_active(self.state):
            start_campaign_runtime(self.state)

        self.runtime = self.state.campaign_runtime
        self.status_message = status_message or "Campaign active."
        self.last_update_ticks = pygame.time.get_ticks()
        self.rng = None

        self.campaign_complete = False
        self.campaign_started = False

        self.map_rect = pygame.Rect(30, 120, 1820, 760)
        self.footer_rect = pygame.Rect(30, 900, 1820, 130)
        self.summary_rect = pygame.Rect(420, 220, 1000, 500)

    def handle_event(self, event):
        if self.handle_buttons_click(event, self.build_buttons()):
            return

        if self.campaign_complete:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", None) == 1:
            if self.handle_task_click(event.pos):
                return

    def update(self, mouse_pos):
        super().update(mouse_pos)

        if self.campaign_complete:
            return

        now_ticks = pygame.time.get_ticks()
        delta_seconds = max(0.0, (now_ticks - self.last_update_ticks) / 1000.0)
        self.last_update_ticks = now_ticks

        self.runtime.paused = False
        tick_campaign_runtime(self.runtime, self.state, delta_seconds, self.rng)

        if self.detect_campaign_started():
            self.campaign_started = True

        if self.should_end_campaign():
            self.runtime.paused = True
            self.runtime.active = False
            self.campaign_complete = True
            self.status_message = "Campaign complete."

            if self.on_save_game:
                self.on_save_game()

    def draw(self, screen):
        self.clear_screen(screen)
        self.draw_header(screen)
        self.draw_map_panel(screen)
        self.draw_footer_roster(screen)

        if self.campaign_complete:
            self.draw_campaign_complete_overlay(screen)

        self.update_and_draw_buttons(screen, self.build_buttons())

    def draw_header(self, screen):
        HeaderPanel(
            rect=(30, 20, 1820, 80),
            title="Campaign Dispatch",
            stats="",
            status_message=self.status_message,
            stats_pos=(50, 58),
            status_pos=(1140, 88),
        ).draw(screen, self.title_font, self.header_font, self.font)

        summary_x = 760
        summary_y = 43
        items = [
            f"Gold {self.state.gold}g",
            f"Time {self.runtime.elapsed_time:.1f}",
            f"Tasks {self.live_task_count()}",
            f"Ready {self.available_hero_count()}",
        ]

        x = summary_x
        for item in items:
            text = self.font.render(item, True, theme.TEXT_PRIMARY)
            screen.blit(text, (x, summary_y))
            x += text.get_width() + 40

    def draw_map_panel(self, screen):
        pygame.draw.rect(screen, (38, 42, 52), self.map_rect, border_radius=14)
        pygame.draw.rect(screen, (88, 96, 120), self.map_rect, 2, border_radius=14)

        inner = self.map_inner_rect()
        pygame.draw.rect(screen, (30, 55, 50), inner, border_radius=10)
        pygame.draw.rect(screen, (60, 90, 82), inner, 2, border_radius=10)

        self.draw_home_base(screen)
        self.draw_tasks(screen)
        self.draw_hero_icons(screen)

    def draw_home_base(self, screen):
        home_pos = self.world_to_screen(CAMPAIGN_HOME_BASE_POSITION)
        pygame.draw.circle(screen, (215, 190, 105), home_pos, 20)
        pygame.draw.circle(screen, (245, 235, 170), home_pos, 20, 2)

        label = self.small_font.render("Guild", True, theme.TEXT_PRIMARY)
        screen.blit(label, (home_pos[0] + 22, home_pos[1] - 10))

    def draw_tasks(self, screen):
        for task in self.runtime.active_tasks:
            if task.is_terminal():
                continue

            pos = self.world_to_screen(task.map_position)

            color = (210, 145, 90)
            if task.state == TASK_STATE_TRAVELING_TO:
                color = (95, 165, 225)
            elif task.state == TASK_STATE_ACTIVE:
                color = (200, 185, 95)
            elif task.state == TASK_STATE_WAITING_FOR_DECISION:
                color = (215, 105, 105)
            elif task.state == TASK_STATE_AWAITING_ACK:
                color = (110, 205, 120)

            pygame.draw.circle(screen, color, pos, 18)
            pygame.draw.circle(screen, (245, 245, 250), pos, 18, 2)

            task_text = truncate_text(task.task_type, self.small_font, 130)
            screen.blit(
                self.small_font.render(task_text, True, theme.TEXT_PRIMARY),
                (pos[0] + 24, pos[1] - 14),
            )

            self.draw_task_chip(screen, task, pos)

    def draw_task_chip(self, screen, task, pos):
        if task.state == TASK_STATE_PENDING:
            remaining = max(0.0, task.expire_time - self.runtime.elapsed_time)
            text = f"{remaining:.0f}s"
            style = "good"
            if remaining <= 8:
                style = "danger"
            elif remaining <= 14:
                style = "warning"
        elif task.state == TASK_STATE_ACTIVE:
            text = f"{self.task_completion_time_remaining(task):.0f}s"
            style = "info"
        elif task.state == TASK_STATE_WAITING_FOR_DECISION:
            text = "Decision"
            style = "danger"
        elif task.state == TASK_STATE_AWAITING_ACK:
            text = "Review"
            style = "good"
        else:
            return

        StatusChip(
            rect=(pos[0] - 22, pos[1] + 24, 82, 24),
            text=text,
            style=style,
        ).draw(screen, self.small_font)

    def draw_hero_icons(self, screen):
        for hero in self.state.roster:
            hero_state = self.runtime.hero_states.get(hero.name)
            if hero_state is None:
                continue

            position = self.hero_screen_position(hero.name)
            if position is None:
                continue

            color = (170, 220, 170)
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

            pygame.draw.circle(screen, color, position, 11)
            pygame.draw.circle(screen, (245, 245, 250), position, 11, 1)

            initials = hero.name[:2].upper()
            text = self.small_font.render(initials, True, (20, 20, 24))
            screen.blit(text, text.get_rect(center=position))

    def draw_footer_roster(self, screen):
        pygame.draw.rect(screen, (34, 34, 42), self.footer_rect, border_radius=14)
        pygame.draw.rect(screen, (82, 88, 110), self.footer_rect, 2, border_radius=14)

        title = self.font.render("Roster", True, theme.TEXT_PRIMARY)
        screen.blit(title, (self.footer_rect.x + 20, self.footer_rect.y + 12))

        cards = self.footer_card_rects()
        visible_roster = self.state.roster[:len(cards)]

        for hero, rect in zip(visible_roster, cards):
            hero_state = self.runtime.hero_states.get(hero.name)
            state_text = hero_state.state if hero_state else "unknown"

            fill = (52, 52, 62)
            if state_text == HERO_STATE_AVAILABLE:
                fill = (48, 62, 52)
            elif state_text == HERO_STATE_RESTING:
                fill = (58, 58, 64)
            elif state_text == HERO_STATE_RETURNING:
                fill = (72, 58, 42)
            elif state_text in (HERO_STATE_TRAVELING, HERO_STATE_ON_TASK, HERO_STATE_AWAITING_DECISION):
                fill = (42, 58, 72)

            pygame.draw.rect(screen, fill, rect, border_radius=10)
            pygame.draw.rect(screen, (92, 96, 112), rect, 1, border_radius=10)

            name = truncate_text(hero.name, self.small_font, rect.width - 12)
            klass = truncate_text(getattr(hero, "hero_class", "Hero"), self.small_font, rect.width - 12)

            screen.blit(self.small_font.render(name, True, theme.TEXT_PRIMARY), (rect.x + 8, rect.y + 8))
            screen.blit(self.small_font.render(klass, True, theme.TEXT_MUTED), (rect.x + 8, rect.y + 28))

            detail = self.hero_state_detail_text(hero_state)
            screen.blit(
                self.small_font.render(
                    truncate_text(detail, self.small_font, rect.width - 12),
                    True,
                    theme.TEXT_MUTED,
                ),
                (rect.x + 8, rect.y + 48),
            )

            badge_text = self.hero_footer_badge_text(hero_state)
            badge_style = self.hero_state_chip_style(state_text)
            StatusChip(
                rect=(rect.x + 8, rect.bottom - 28, rect.width - 16, 20),
                text=badge_text,
                style=badge_style,
            ).draw(screen, self.small_font)

    def draw_campaign_complete_overlay(self, screen):
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, (34, 34, 42), self.summary_rect, border_radius=16)
        pygame.draw.rect(screen, (104, 112, 138), self.summary_rect, 2, border_radius=16)

        title = self.title_font.render("Campaign Complete", True, theme.TEXT_PRIMARY)
        screen.blit(title, (self.summary_rect.x + 28, self.summary_rect.y + 24))

        lines = [
            f"Campaign Time: {self.runtime.elapsed_time:.1f}",
            f"Remaining Live Tasks: {self.live_task_count()}",
            f"Ready Heroes: {self.available_hero_count()}",
            f"Roster Size: {len(self.state.roster)}",
            "",
            "All tasks have been resolved and all heroes have returned to the guild.",
            "Resting heroes will recover during campaign-cycle processing.",
            "",
            "Press Continue to resolve campaign results and return to the guild hall.",
        ]

        y = self.summary_rect.y + 90
        for line in lines:
            if line == "":
                y += 22
                continue

            text = self.font.render(line, True, theme.TEXT_SECONDARY)
            screen.blit(text, (self.summary_rect.x + 28, y))
            y += 34

    def build_buttons(self):
        if self.campaign_complete:
            return [
                Button(
                    (self.summary_rect.centerx - 110, self.summary_rect.bottom - 72, 220, 42),
                    "Continue",
                    self.finish_campaign,
                ),
            ]

        return []

    def finish_campaign(self):
        self.on_campaign_complete()

    def handle_task_click(self, pos):
        if self.campaign_complete:
            return False

        for task in self.runtime.active_tasks:
            if task.is_terminal():
                continue

            icon_center = self.world_to_screen(task.map_position)
            icon_rect = pygame.Rect(icon_center[0] - 24, icon_center[1] - 24, 48, 48)
            label_rect = pygame.Rect(icon_center[0] + 18, icon_center[1] - 18, 150, 30)
            chip_rect = pygame.Rect(icon_center[0] - 26, icon_center[1] + 22, 96, 28)

            if icon_rect.collidepoint(pos) or label_rect.collidepoint(pos) or chip_rect.collidepoint(pos):
                self.on_open_task(task.task_id)
                return True

        return False

    def detect_campaign_started(self):
        if self.live_task_count() > 0:
            return True

        if self.has_active_field_heroes():
            return True

        for hero in self.state.roster:
            if getattr(hero, "participated_this_cycle", False):
                return True

        return False

    def should_end_campaign(self):
        if not self.campaign_started:
            return False

        if self.has_unresolved_tasks():
            return False

        if self.has_active_field_heroes():
            return False

        return True

    def has_unresolved_tasks(self):
        for task in self.runtime.active_tasks:
            if task.state in (
                TASK_STATE_PENDING,
                TASK_STATE_TRAVELING_TO,
                TASK_STATE_ACTIVE,
                TASK_STATE_WAITING_FOR_DECISION,
                TASK_STATE_AWAITING_ACK,
            ):
                return True
        return False

    def has_active_field_heroes(self):
        for hero in self.state.roster:
            hero_state = self.runtime.hero_states.get(hero.name)
            if hero_state is None:
                continue

            if hero_state.state in (
                HERO_STATE_TRAVELING,
                HERO_STATE_ON_TASK,
                HERO_STATE_AWAITING_DECISION,
                HERO_STATE_RETURNING,
            ):
                return True

        return False

    def live_task_count(self):
        return sum(1 for task in self.runtime.active_tasks if not task.is_terminal())

    def available_hero_count(self):
        count = 0
        for hero in self.state.roster:
            hero_state = self.runtime.hero_states.get(hero.name)
            if hero_state and hero_state.state == HERO_STATE_AVAILABLE:
                count += 1
        return count

    def footer_card_rects(self):
        cards = []
        start_x = self.footer_rect.x + 18
        y = self.footer_rect.y + 42
        width = 205
        height = 76
        gap = 10

        max_cards = max(1, (self.footer_rect.width - 36 + gap) // (width + gap))
        x = start_x
        for _ in range(min(len(self.state.roster), max_cards)):
            cards.append(pygame.Rect(x, y, width, height))
            x += width + gap

        return cards

    def map_inner_rect(self):
        return pygame.Rect(
            self.map_rect.x + 18,
            self.map_rect.y + 18,
            self.map_rect.width - 36,
            self.map_rect.height - 36,
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
                return f"On {truncate_text(task.task_type, self.small_font, 120)}"
            return "Working"

        if hero_state.state == HERO_STATE_AWAITING_DECISION:
            return "Awaiting decision"

        if hero_state.state == HERO_STATE_RETURNING:
            return "Returning to guild"

        return "Ready"

    def hero_footer_badge_text(self, hero_state):
        if hero_state is None:
            return "unknown"

        if hero_state.state == HERO_STATE_RESTING and hero_state.rest_end_time is not None:
            remaining = max(0.0, hero_state.rest_end_time - self.runtime.elapsed_time)
            return f"rest {remaining:.0f}s"

        return hero_state.state.replace("_", " ")

    def task_completion_time_remaining(self, task):
        if task.state not in (TASK_STATE_ACTIVE, TASK_STATE_WAITING_FOR_DECISION):
            return 0.0

        if task.active_until is None:
            return task.task_duration if task.state == TASK_STATE_WAITING_FOR_DECISION else 0.0

        return max(0.0, task.active_until - self.runtime.elapsed_time)