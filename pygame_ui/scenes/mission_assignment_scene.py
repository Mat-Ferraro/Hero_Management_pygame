import pygame

from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.ui_helpers import truncate_text, wrap_text
from pygame_ui.widgets.button import Button
from pygame_ui.widgets.status_chip import StatusChip
from systems.campaign.campaign_constants import (
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
from systems.campaign.campaign_runtime import acknowledge_completed_task, resolve_open_decision
from systems.campaign.task_dispatch import assign_heroes_to_task, find_task
from systems.campaign.task_resolution import (
    combined_party_dispatch_stats,
    evaluate_stat_rule,
    format_dispatch_stats,
    format_stat_rule_short,
    get_task_stat_rules,
    hero_dispatch_stats,
)


DISPLAY_STAT_LABELS = {
    "might": "Might",
    "guard": "Guard",
    "wit": "Wit",
    "presence": "Presence",
    "swift": "Swift",
}

ORDERED_STATS = ["might", "guard", "wit", "presence", "swift"]


class MissionAssignmentScene(SceneBase):
    def __init__(self, state, task_id, on_return_to_campaign, on_save_game):
        super().__init__()

        self.state = state
        self.task_id = task_id
        self.on_return_to_campaign = on_return_to_campaign
        self.on_save_game = on_save_game

        self.runtime = getattr(state, "campaign_runtime", None)
        self.status_message = ""

        self.staged_team_names = []

        self.result_animation_started = False
        self.result_animation_done = False
        self.result_animation_start_ticks = 0
        self.result_animation_duration_ms = 1100
        self.result_display_value = 0.0

        task = self.current_task()
        if task is not None and getattr(task, "assigned_heroes", None):
            self.staged_team_names = list(task.assigned_heroes)

        if task is not None and task.state == TASK_STATE_AWAITING_ACK:
            self.start_result_animation()

    # -------------------------------------------------------------------------
    # Runtime access
    # -------------------------------------------------------------------------

    def current_task(self):
        if self.runtime is None:
            return None
        return find_task(self.runtime, self.task_id)

    def current_decision_event(self):
        if self.runtime is None:
            return None

        event = getattr(self.runtime, "open_decision_event", None)
        if event is None:
            return None

        if getattr(event, "task_id", None) != self.task_id:
            return None

        return event

    def scene_mode(self, task):
        if task is None:
            return "missing"

        if self.current_decision_event() is not None:
            return "decision"

        if task.state == TASK_STATE_PENDING:
            return "assignment"

        if task.state == TASK_STATE_AWAITING_ACK:
            return "review"

        return "readonly"

    # -------------------------------------------------------------------------
    # Animation
    # -------------------------------------------------------------------------

    def start_result_animation(self):
        if self.result_animation_started:
            return

        self.result_animation_started = True
        self.result_animation_done = False
        self.result_animation_start_ticks = pygame.time.get_ticks()
        self.result_display_value = 0.0

    def update_result_animation(self):
        task = self.current_task()
        if task is None or task.state != TASK_STATE_AWAITING_ACK:
            self.result_animation_started = False
            self.result_animation_done = False
            self.result_display_value = 0.0
            return

        if not self.result_animation_started:
            self.start_result_animation()

        target_value = max(0.0, min(1.0, float(getattr(task, "success_chance", 0.0))))
        elapsed_ms = max(0, pygame.time.get_ticks() - self.result_animation_start_ticks)

        if elapsed_ms >= self.result_animation_duration_ms:
            self.result_display_value = target_value
            self.result_animation_done = True
            return

        progress = elapsed_ms / float(self.result_animation_duration_ms)
        self.result_display_value = target_value * progress
        self.result_animation_done = False

    # -------------------------------------------------------------------------
    # Pygame lifecycle
    # -------------------------------------------------------------------------

    def handle_event(self, event):
        if self.handle_buttons_click(event, self.build_buttons()):
            return

        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", None) == 1:
            self.handle_slot_click(event.pos)
            self.handle_hero_card_click(event.pos)

    def update(self, mouse_pos):
        super().update(mouse_pos)
        self.update_result_animation()

    def draw(self, screen):
        self.clear_screen(screen)

        task = self.current_task()
        if task is None:
            screen.blit(self.title_font.render("Mission not found.", True, theme.TEXT_PRIMARY), (60, 60))
            return

        self.draw_header(screen, task)
        self.draw_layout(screen, task)
        self.update_and_draw_buttons(screen, self.build_buttons())

    # -------------------------------------------------------------------------
    # Layout
    # -------------------------------------------------------------------------

    def draw_header(self, screen, task):
        pygame.draw.rect(screen, (34, 34, 42), (30, 20, 1820, 78), border_radius=12)
        pygame.draw.rect(screen, (92, 96, 112), (30, 20, 1820, 78), 2, border_radius=12)

        title = self.title_font.render(task.task_type, True, theme.TEXT_PRIMARY)
        screen.blit(title, (50, 36))

        mode = self.scene_mode(task)
        mode_text = {
            "assignment": "Assignment",
            "decision": "Decision",
            "review": "Review",
            "readonly": self.friendly_task_state(task.state),
            "missing": "Missing",
        }.get(mode, "Mission")

        screen.blit(
            self.font.render(f"Mode: {mode_text}", True, theme.TEXT_SECONDARY),
            (420, 42),
        )

        if self.status_message:
            screen.blit(self.font.render(self.status_message, True, theme.TEXT_PRIMARY), (740, 42))

    def draw_layout(self, screen, task):
        left_rect = pygame.Rect(40, 120, 520, 520)
        center_rect = pygame.Rect(580, 120, 560, 520)
        right_rect = pygame.Rect(1160, 120, 650, 520)
        footer_rect = pygame.Rect(40, 670, 1770, 250)

        self.draw_panel(screen, left_rect, "Mission Details")
        self.draw_panel(screen, center_rect, "Team Assignment")
        self.draw_panel(screen, right_rect, self.right_panel_title(task))
        self.draw_panel(screen, footer_rect, "Available Heroes")

        self.draw_mission_details(screen, task, left_rect)
        self.draw_team_assignment(screen, task, center_rect)
        self.draw_right_panel(screen, task, right_rect)
        self.draw_available_heroes(screen, task, footer_rect)

    def draw_panel(self, screen, rect, title):
        pygame.draw.rect(screen, (34, 34, 42), rect, border_radius=12)
        pygame.draw.rect(screen, (92, 96, 112), rect, 2, border_radius=12)
        text = self.font.render(title, True, theme.TEXT_PRIMARY)
        screen.blit(text, (rect.x + 16, rect.y + 12))

    def right_panel_title(self, task):
        mode = self.scene_mode(task)
        if mode == "decision":
            return "Decision"
        if mode == "review":
            return "Revealed Breakdown"
        return "Mission Hints"

    # -------------------------------------------------------------------------
    # Left panel
    # -------------------------------------------------------------------------

    def draw_mission_details(self, screen, task, rect):
        y = rect.y + 56

        rows = [
            f"Task: {task.task_type}",
            f"Difficulty: {getattr(task, 'difficulty', 1)}",
            f"Duration: {float(getattr(task, 'task_duration', 0.0)):.1f}s",
            f"Reward: {getattr(task, 'reward_gold_min', 0)}-{getattr(task, 'reward_gold_max', 0)}g / {getattr(task, 'reward_xp', 0)} XP",
            f"Max Heroes: {getattr(task, 'max_heroes', 1)}",
            f"Preferred Classes: {', '.join(getattr(task, 'preferred_classes', []) or []) or 'Any'}",
        ]

        for row in rows:
            screen.blit(self.font.render(row, True, theme.TEXT_PRIMARY), (rect.x + 20, y))
            y += 28

        y += 14
        for line in self.mission_story_lines(task):
            for wrapped in wrap_text(line, self.small_font, rect.width - 40):
                screen.blit(self.small_font.render(wrapped, True, theme.TEXT_SECONDARY), (rect.x + 20, y))
                y += 20
            y += 6

        mode = self.scene_mode(task)

        if mode == "decision":
            decision_event = self.current_decision_event()
            if decision_event is not None:
                y += 12
                screen.blit(self.font.render("Decision Required", True, theme.TEXT_PRIMARY), (rect.x + 20, y))
                y += 30

                description = str(getattr(decision_event, "description", ""))
                for wrapped in wrap_text(description, self.small_font, rect.width - 40):
                    screen.blit(self.small_font.render(wrapped, True, theme.TEXT_SECONDARY), (rect.x + 20, y))
                    y += 20

        elif mode == "review":
            y += 12
            screen.blit(self.font.render("Mission Result", True, theme.TEXT_PRIMARY), (rect.x + 20, y))
            y += 30

            self.draw_result_bar(screen, rect.x + 20, y, rect.width - 40, 28, task)
            y += 44

            if self.result_animation_done:
                for row in self.build_result_rows(task):
                    for wrapped in wrap_text(row, self.small_font, rect.width - 40):
                        screen.blit(self.small_font.render(wrapped, True, theme.TEXT_SECONDARY), (rect.x + 20, y))
                        y += 20
                    y += 4
            else:
                screen.blit(
                    self.small_font.render("Resolving outcome...", True, theme.TEXT_SECONDARY),
                    (rect.x + 20, y),
                )

    def draw_result_bar(self, screen, x, y, width, height, task):
        bg_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, (42, 42, 52), bg_rect, border_radius=8)
        pygame.draw.rect(screen, (92, 96, 112), bg_rect, 1, border_radius=8)

        fail_cutoff = 0.45
        partial_cutoff = 0.70
        success_cutoff = 0.90

        for cutoff in (fail_cutoff, partial_cutoff, success_cutoff):
            cut_x = x + int(width * cutoff)
            pygame.draw.line(screen, (120, 120, 135), (cut_x, y), (cut_x, y + height), 1)

        fill_width = max(0, min(width, int(width * self.result_display_value)))
        if fill_width > 0:
            fill_rect = pygame.Rect(x, y, fill_width, height)
            pygame.draw.rect(screen, (185, 150, 70), fill_rect, border_radius=8)

        label_y = y + height + 6
        labels = [
            ("Critical", 0.00),
            ("Partial", 0.45),
            ("Success", 0.70),
            ("Great", 0.90),
        ]
        for label, frac in labels:
            tx = x + int(width * frac)
            screen.blit(self.small_font.render(label, True, theme.TEXT_MUTED), (tx, label_y))

    # -------------------------------------------------------------------------
    # Center panel
    # -------------------------------------------------------------------------

    def draw_team_assignment(self, screen, task, rect):
        mode = self.scene_mode(task)
        staged_heroes = self.staged_team()

        staged_stats = combined_party_dispatch_stats(staged_heroes) if staged_heroes else {
            "might": 0,
            "guard": 0,
            "wit": 0,
            "presence": 0,
            "swift": 0,
        }

        y = rect.y + 54
        screen.blit(self.font.render("Current Team", True, theme.TEXT_PRIMARY), (rect.x + 20, y))
        y += 34

        slot_rects = self.slot_rects(rect, task.max_heroes)
        for index, slot_rect in enumerate(slot_rects):
            self.draw_team_slot(screen, slot_rect, index, task)

        if mode == "review":
            compare_y = rect.y + 178
            screen.blit(self.font.render("Revealed Overlap", True, theme.TEXT_PRIMARY), (rect.x + 20, compare_y))
            compare_y += 32

            stat_rules = get_task_stat_rules(task)
            for stat_key in ORDERED_STATS:
                self.draw_stat_comparison_row(
                    screen=screen,
                    x=rect.x + 20,
                    y=compare_y,
                    width=rect.width - 40,
                    stat_key=stat_key,
                    assigned_value=int(staged_stats.get(stat_key, 0)),
                    rule=stat_rules.get(stat_key, {"mode": "minimum", "target": 0}),
                )
                compare_y += 42

            preview_y = rect.y + 420
            for row in self.team_preview_rows(task, staged_heroes):
                screen.blit(self.small_font.render(row, True, theme.TEXT_SECONDARY), (rect.x + 20, preview_y))
                preview_y += 22

            summary_y = rect.y + 486
            screen.blit(
                self.small_font.render(format_dispatch_stats(staged_stats), True, theme.TEXT_PRIMARY),
                (rect.x + 20, summary_y),
            )
            return

        stats_y = rect.y + 180
        screen.blit(self.font.render("Team Totals", True, theme.TEXT_PRIMARY), (rect.x + 20, stats_y))
        stats_y += 36

        for stat_key in ORDERED_STATS:
            self.draw_stat_row(
                screen=screen,
                x=rect.x + 20,
                y=stats_y,
                label=DISPLAY_STAT_LABELS[stat_key],
                value=int(staged_stats.get(stat_key, 0)),
                width=360,
            )
            stats_y += 40

        preview_y = rect.y + 395
        for row in self.team_preview_rows(task, staged_heroes):
            screen.blit(self.small_font.render(row, True, theme.TEXT_SECONDARY), (rect.x + 20, preview_y))
            preview_y += 22

        summary_y = rect.y + 486
        screen.blit(
            self.small_font.render(format_dispatch_stats(staged_stats), True, theme.TEXT_PRIMARY),
            (rect.x + 20, summary_y),
        )

    def draw_stat_row(self, screen, x, y, label, value, width):
        label_text = self.small_font.render(label, True, theme.TEXT_PRIMARY)
        value_text = self.small_font.render(str(value), True, theme.TEXT_PRIMARY)
        screen.blit(label_text, (x, y))

        bar_x = x + 110
        bar_y = y + 4
        bar_w = width
        bar_h = 14

        pygame.draw.rect(screen, (42, 42, 52), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
        fill_w = max(0, min(bar_w, int((value / 12.0) * bar_w)))
        pygame.draw.rect(screen, (185, 150, 70), (bar_x, bar_y, fill_w, bar_h), border_radius=6)

        screen.blit(value_text, (bar_x + bar_w + 10, y))

    def draw_stat_comparison_row(self, screen, x, y, width, stat_key, assigned_value, rule):
        label = DISPLAY_STAT_LABELS.get(stat_key, stat_key.title())
        label_surface = self.small_font.render(label, True, theme.TEXT_PRIMARY)
        screen.blit(label_surface, (x, y + 2))

        rule_text = format_stat_rule_short(rule)
        rule_surface = self.small_font.render(rule_text, True, theme.TEXT_MUTED)
        screen.blit(rule_surface, (x + 82, y + 2))

        score = evaluate_stat_rule(assigned_value, rule)["score"]
        score_percent = f"{score:.0%}"
        score_color = (
            (120, 200, 120) if score >= 0.99
            else ((210, 180, 90) if score >= 0.70 else (200, 110, 110))
        )
        score_surface = self.small_font.render(score_percent, True, score_color)
        screen.blit(score_surface, (x + width - score_surface.get_width(), y + 2))

        track_x = x + 170
        track_y = y + 18
        track_w = width - 240
        track_h = 14

        pygame.draw.rect(screen, (42, 42, 52), (track_x, track_y, track_w, track_h), border_radius=7)
        pygame.draw.rect(screen, (74, 76, 92), (track_x, track_y, track_w, track_h), 1, border_radius=7)

        mode = str(rule.get("mode", "minimum")).lower()

        if mode == "range":
            min_value = int(rule.get("min", 0))
            max_value = max(min_value, int(rule.get("max", min_value)))
            scale_max = max(1, assigned_value, max_value)

            band_start = int(track_w * (min_value / scale_max))
            band_width = max(2, int(track_w * ((max_value - min_value) / scale_max))) if max_value > min_value else 2
            pygame.draw.rect(
                screen,
                (80, 110, 150),
                (track_x + band_start, track_y, band_width, track_h),
                border_radius=7,
            )

            assigned_w = int(track_w * (assigned_value / scale_max))
            if assigned_w > 0:
                pygame.draw.rect(
                    screen,
                    (185, 150, 70),
                    (track_x, track_y, assigned_w, track_h),
                    border_radius=7,
                )

        elif mode == "maximum":
            target = int(rule.get("target", 0))
            scale_max = max(1, assigned_value, target)

            allowed_w = int(track_w * (target / scale_max))
            if allowed_w > 0:
                pygame.draw.rect(
                    screen,
                    (70, 110, 90),
                    (track_x, track_y, allowed_w, track_h),
                    border_radius=7,
                )

            assigned_w = int(track_w * (assigned_value / scale_max))
            if assigned_w > 0:
                assigned_color = (185, 150, 70) if assigned_value <= target else (180, 95, 95)
                pygame.draw.rect(
                    screen,
                    assigned_color,
                    (track_x, track_y, assigned_w, track_h),
                    border_radius=7,
                )

        else:
            target = int(rule.get("target", 0))
            scale_max = max(1, assigned_value, target)

            target_w = int(track_w * (target / scale_max))
            if target_w > 0:
                pygame.draw.rect(
                    screen,
                    (80, 110, 150),
                    (track_x, track_y, target_w, track_h),
                    border_radius=7,
                )

            assigned_w = int(track_w * (assigned_value / scale_max))
            if assigned_w > 0:
                pygame.draw.rect(
                    screen,
                    (185, 150, 70),
                    (track_x, track_y, assigned_w, track_h),
                    border_radius=7,
                )

        value_surface = self.small_font.render(str(assigned_value), True, theme.TEXT_PRIMARY)
        screen.blit(value_surface, (track_x + track_w + 8, y + 16))

    def draw_team_slot(self, screen, slot_rect, index, task):
        is_filled = index < len(self.staged_team_names)

        fill = (48, 48, 60) if not is_filled else (56, 66, 84)
        pygame.draw.rect(screen, fill, slot_rect, border_radius=8)
        pygame.draw.rect(screen, (98, 102, 120), slot_rect, 1, border_radius=8)

        if is_filled:
            hero_name = self.staged_team_names[index]
            hero = self.find_hero(hero_name)
            label = hero.name if hero else hero_name
            klass = getattr(hero, "hero_class", "Hero") if hero else "Hero"

            screen.blit(
                self.small_font.render(
                    truncate_text(label, self.small_font, slot_rect.width - 12),
                    True,
                    theme.TEXT_PRIMARY,
                ),
                (slot_rect.x + 8, slot_rect.y + 8),
            )
            screen.blit(
                self.small_font.render(
                    truncate_text(klass, self.small_font, slot_rect.width - 12),
                    True,
                    theme.TEXT_MUTED,
                ),
                (slot_rect.x + 8, slot_rect.y + 28),
            )

            chip_label = "Assigned" if self.scene_mode(task) == "assignment" else self.friendly_task_state(task.state)
            chip_style = "info" if self.scene_mode(task) == "assignment" else "warning"
            StatusChip(
                rect=(slot_rect.x + 8, slot_rect.bottom - 26, slot_rect.width - 16, 18),
                text=chip_label,
                style=chip_style,
            ).draw(screen, self.small_font)
        else:
            placeholder = self.small_font.render("Empty Slot", True, theme.TEXT_MUTED)
            screen.blit(placeholder, (slot_rect.x + 8, slot_rect.y + 14))

            if self.scene_mode(task) == "assignment":
                hint = self.small_font.render("Click a hero below", True, theme.TEXT_MUTED)
                screen.blit(hint, (slot_rect.x + 8, slot_rect.y + 34))

    # -------------------------------------------------------------------------
    # Right panel
    # -------------------------------------------------------------------------

    def draw_right_panel(self, screen, task, rect):
        mode = self.scene_mode(task)

        if mode == "decision":
            self.draw_decision_panel(screen, task, rect)
            return

        if mode == "review":
            self.draw_review_panel(screen, task, rect)
            return

        self.draw_hint_panel(screen, task, rect)

    def draw_hint_panel(self, screen, task, rect):
        y = rect.y + 56
        for hint in self.generate_hints(task):
            bullet = f"• {hint}"
            for wrapped in wrap_text(bullet, self.font, rect.width - 40):
                screen.blit(self.font.render(wrapped, True, theme.TEXT_PRIMARY), (rect.x + 20, y))
                y += 26
            y += 10

    def draw_decision_panel(self, screen, task, rect):
        y = rect.y + 56
        decision_event = self.current_decision_event()
        if decision_event is None:
            screen.blit(self.font.render("No decision available.", True, theme.TEXT_MUTED), (rect.x + 20, y))
            return

        title = str(getattr(decision_event, "title", "Decision"))
        screen.blit(self.font.render(title, True, theme.TEXT_PRIMARY), (rect.x + 20, y))
        y += 34

        description = str(getattr(decision_event, "description", ""))
        for wrapped in wrap_text(description, self.small_font, rect.width - 40):
            screen.blit(self.small_font.render(wrapped, True, theme.TEXT_SECONDARY), (rect.x + 20, y))
            y += 20

        y += 18
        for choice in self.iter_decision_choices(decision_event):
            label = self.decision_choice_label(choice)
            description = self.decision_choice_description(choice)

            pygame.draw.rect(screen, (48, 48, 60), (rect.x + 20, y, rect.width - 40, 70), border_radius=8)
            pygame.draw.rect(screen, (98, 102, 120), (rect.x + 20, y, rect.width - 40, 70), 1, border_radius=8)

            screen.blit(self.small_font.render(label, True, theme.TEXT_PRIMARY), (rect.x + 32, y + 10))

            line_y = y + 32
            for wrapped in wrap_text(description or "Choose how the team should proceed.", self.small_font, rect.width - 64):
                screen.blit(self.small_font.render(wrapped, True, theme.TEXT_MUTED), (rect.x + 32, line_y))
                line_y += 18
                if line_y > y + 52:
                    break

            y += 84

    def draw_review_panel(self, screen, task, rect):
        y = rect.y + 56

        rows = [
            f"Outcome Band: {self.outcome_label_from_band(getattr(task, 'outcome_band', ''))}",
            f"Resolved Chance: {float(getattr(task, 'success_chance', 0.0)):.0%}",
            f"Team Fit: {float(getattr(task, 'coverage_ratio', 0.0)):.0%}",
            f"Payout Multiplier: {float(getattr(task, 'payout_multiplier', 1.0)):.2f}x",
            f"XP Multiplier: {float(getattr(task, 'xp_multiplier', 1.0)):.2f}x",
        ]

        for row in rows:
            screen.blit(self.font.render(row, True, theme.TEXT_PRIMARY), (rect.x + 20, y))
            y += 28

        y += 14
        screen.blit(self.font.render("Consequences", True, theme.TEXT_PRIMARY), (rect.x + 20, y))
        y += 28

        summary_lines = list(getattr(task, "consequence_summary", []) or [])
        if not summary_lines:
            summary_lines = ["No consequence details were recorded."]

        for line in summary_lines[:12]:
            for wrapped in wrap_text(f"• {line}", self.small_font, rect.width - 40):
                screen.blit(self.small_font.render(wrapped, True, theme.TEXT_SECONDARY), (rect.x + 20, y))
                y += 20
            y += 4

    # -------------------------------------------------------------------------
    # Footer
    # -------------------------------------------------------------------------

    def draw_available_heroes(self, screen, task, rect):
        visible = self.state.roster[:10]
        card_rects = self.hero_card_rects(rect, len(visible))
        mode = self.scene_mode(task)

        for hero, card_rect in zip(visible, card_rects):
            hero_state = self.runtime.hero_states.get(hero.name) if self.runtime else None
            state_text = hero_state.state if hero_state else "unknown"
            is_staged = hero.name in self.staged_team_names
            is_clickable = (
                mode == "assignment"
                and hero_state is not None
                and hero_state.state == HERO_STATE_AVAILABLE
            )

            fill = (52, 52, 62)
            border = (98, 102, 120)

            if state_text == HERO_STATE_AVAILABLE:
                fill = (48, 62, 52)
            elif state_text == HERO_STATE_RESTING:
                fill = (58, 58, 64)
            elif state_text == HERO_STATE_RETURNING:
                fill = (72, 58, 42)
            elif state_text in (HERO_STATE_TRAVELING, HERO_STATE_ON_TASK, HERO_STATE_AWAITING_DECISION):
                fill = (42, 58, 72)

            if is_staged:
                fill = (62, 74, 92)
                border = (135, 160, 210)
            elif mode == "assignment" and not is_clickable:
                fill = (46, 46, 50)

            pygame.draw.rect(screen, fill, card_rect, border_radius=10)
            pygame.draw.rect(screen, border, card_rect, 1, border_radius=10)

            name_color = theme.TEXT_PRIMARY if (is_clickable or is_staged or mode != "assignment") else theme.TEXT_MUTED

            screen.blit(
                self.small_font.render(
                    truncate_text(hero.name, self.small_font, card_rect.width - 12),
                    True,
                    name_color,
                ),
                (card_rect.x + 8, card_rect.y + 8),
            )
            screen.blit(
                self.small_font.render(
                    truncate_text(getattr(hero, "hero_class", "Hero"), self.small_font, card_rect.width - 12),
                    True,
                    theme.TEXT_MUTED,
                ),
                (card_rect.x + 8, card_rect.y + 28),
            )

            stat_text = format_dispatch_stats(hero_dispatch_stats(hero))
            screen.blit(
                self.small_font.render(
                    truncate_text(stat_text, self.small_font, card_rect.width - 12),
                    True,
                    theme.TEXT_MUTED,
                ),
                (card_rect.x + 8, card_rect.y + 48),
            )

            chip_text = "Assigned Here" if is_staged else self.friendly_hero_state(state_text)
            chip_style = "info" if is_staged else self.hero_state_chip_style(state_text)
            StatusChip(
                rect=(card_rect.x + 8, card_rect.bottom - 24, card_rect.width - 16, 18),
                text=chip_text,
                style=chip_style,
            ).draw(screen, self.small_font)

    # -------------------------------------------------------------------------
    # Buttons / interactions
    # -------------------------------------------------------------------------

    def build_buttons(self):
        buttons = [
            Button((1640, 44, 150, 34), "Back", self.return_to_campaign),
        ]

        task = self.current_task()
        if task is None:
            return buttons

        bottom_padding = 24
        right_padding = 40
        button_width = 280
        button_height = 42
        button_x = 1920 - right_padding - button_width
        button_y = 1080 - bottom_padding - button_height

        mode = self.scene_mode(task)

        if mode == "decision":
            decision_event = self.current_decision_event()
            if decision_event is None:
                return buttons

            choice_width = 220
            choice_gap = 18
            choices = self.iter_decision_choices(decision_event)[:3]
            total_width = (len(choices) * choice_width) + (max(0, len(choices) - 1) * choice_gap)
            start_x = 1920 - right_padding - total_width

            for index, choice in enumerate(choices):
                choice_id = self.decision_choice_id(choice)
                label = self.decision_choice_label(choice) or "Choose"
                buttons.append(
                    Button(
                        (start_x + index * (choice_width + choice_gap), button_y, choice_width, button_height),
                        label,
                        lambda cid=choice_id: self.resolve_decision_choice(cid),
                    )
                )
            return buttons

        if mode == "assignment":
            buttons.append(
                Button((button_x, button_y, button_width, button_height), "Dispatch", self.dispatch_staged_team)
            )
        elif mode == "review" and self.result_animation_done:
            buttons.append(
                Button((button_x, button_y, button_width, button_height), "Return Heroes", self.acknowledge_results)
            )

        return buttons

    def handle_slot_click(self, pos):
        task = self.current_task()
        if task is None or self.scene_mode(task) != "assignment":
            return

        for index, rect in enumerate(self.slot_rects(pygame.Rect(580, 120, 560, 520), task.max_heroes)):
            if rect.collidepoint(pos):
                if index < len(self.staged_team_names):
                    removed = self.staged_team_names.pop(index)
                    self.status_message = f"Removed {removed}."
                return

    def handle_hero_card_click(self, pos):
        task = self.current_task()
        if task is None or self.scene_mode(task) != "assignment":
            return

        visible = self.state.roster[:10]
        rects = self.hero_card_rects(pygame.Rect(40, 670, 1770, 250), len(visible))

        for hero, rect in zip(visible, rects):
            if not rect.collidepoint(pos):
                continue

            hero_state = self.runtime.hero_states.get(hero.name) if self.runtime else None

            if hero.name in self.staged_team_names:
                self.staged_team_names.remove(hero.name)
                self.status_message = f"Removed {hero.name}."
                return

            if hero_state is None or hero_state.state != HERO_STATE_AVAILABLE:
                self.status_message = f"{hero.name} is not available."
                return

            if len(self.staged_team_names) >= task.max_heroes:
                self.status_message = f"This mission allows only {task.max_heroes} heroes."
                return

            self.staged_team_names.append(hero.name)
            self.status_message = f"Added {hero.name}."
            return

    def dispatch_staged_team(self):
        task = self.current_task()
        if task is None:
            self.status_message = "Mission not found."
            return

        if self.scene_mode(task) != "assignment":
            self.status_message = "This mission is no longer assignable."
            return

        if not self.staged_team_names:
            self.status_message = "Assign at least one hero."
            return

        success, message = assign_heroes_to_task(
            runtime=self.runtime,
            hero_names=list(self.staged_team_names),
            task_id=task.task_id,
            now=self.runtime.elapsed_time,
        )
        self.status_message = message

        if success:
            if self.on_save_game:
                self.on_save_game()
            self.on_return_to_campaign("Mission dispatched.")

    def acknowledge_results(self):
        task = self.current_task()
        if task is None:
            self.status_message = "Mission not found."
            return

        message = acknowledge_completed_task(
            runtime=self.runtime,
            task_id=task.task_id,
        )
        self.status_message = message

        if self.on_save_game:
            self.on_save_game()

        if "Acknowledged" in message:
            self.on_return_to_campaign("Heroes returning from mission.")

    def resolve_decision_choice(self, choice_id):
        message = resolve_open_decision(self.runtime, choice_id)
        self.status_message = message

        if self.on_save_game:
            self.on_save_game()

        self.on_return_to_campaign("Decision resolved.")

    def return_to_campaign(self):
        if self.on_save_game:
            self.on_save_game()
        self.on_return_to_campaign("Returned to campaign.")

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def staged_team(self):
        heroes = []
        for name in self.staged_team_names:
            hero = self.find_hero(name)
            if hero is not None:
                heroes.append(hero)
        return heroes

    def find_hero(self, hero_name):
        for hero in self.state.roster:
            if hero.name == hero_name:
                return hero
        return None

    def slot_rects(self, rect, count):
        rects = []
        slot_y = rect.y + 86
        slot_x = rect.x + 20
        slot_w = 160
        slot_h = 72
        gap = 12

        for _ in range(count):
            rects.append(pygame.Rect(slot_x, slot_y, slot_w, slot_h))
            slot_x += slot_w + gap

        return rects

    def hero_card_rects(self, rect, count):
        rects = []
        cols = 5
        card_w = 330
        card_h = 92
        gap_x = 14
        gap_y = 14

        start_x = rect.x + 20
        start_y = rect.y + 52

        for index in range(count):
            col = index % cols
            row = index // cols
            x = start_x + col * (card_w + gap_x)
            y = start_y + row * (card_h + gap_y)
            rects.append(pygame.Rect(x, y, card_w, card_h))

        return rects

    def mission_story_lines(self, task):
        return [
            f"A fresh report has arrived concerning {task.task_type.lower()}.",
            "Your guild must weigh speed, survival, and the strengths of the heroes you commit.",
        ]

    def extract_reward_text(self, task):
        summary = str(getattr(task, "outcome_summary", "") or "")
        if "Reward " in summary:
            reward_part = summary.split("Reward ", 1)[1]
            return reward_part.strip()
        return "—"

    def build_result_rows(self, task):
        rows = []

        rows.append(f"Outcome: {self.outcome_label_from_band(getattr(task, 'outcome_band', ''))}")
        rows.append(f"Reward: {self.extract_reward_text(task)}")

        if getattr(task, "injured_heroes", []):
            injured_names = ", ".join(task.injured_heroes[:2])
            if len(task.injured_heroes) > 2:
                injured_names += "..."
            rows.append(f"Injuries: {injured_names}")
        else:
            rows.append("Injuries: None")

        tp_lines = []
        for hero_name, amount in getattr(task, "training_points_by_hero", {}).items():
            if amount > 0:
                tp_lines.append(f"{hero_name} +{amount}")

        if tp_lines:
            rows.append(f"Training: {', '.join(tp_lines[:2])}")
        else:
            rows.append("Training: None")

        return rows

    def team_preview_rows(self, task, staged_heroes):
        mode = self.scene_mode(task)

        if mode == "assignment":
            if staged_heroes:
                return [
                    f"Assigned: {', '.join(hero.name for hero in staged_heroes)}",
                    f"Team Size: {len(staged_heroes)} / {task.max_heroes}",
                    "Exact mission requirements remain hidden until the mission resolves.",
                ]
            return ["Click heroes below to build this team."]

        if mode == "decision":
            return [
                f"Assigned: {', '.join(getattr(task, 'assigned_heroes', []) or []) or 'None'}",
                "Decision pending.",
                "Choose how the mission should proceed.",
            ]

        if getattr(task, "assigned_heroes", []):
            return [
                f"Assigned: {', '.join(task.assigned_heroes)}",
                f"Team Fit: {float(getattr(task, 'coverage_ratio', 0.0)):.0%}" if float(getattr(task, "coverage_ratio", 0.0)) > 0 else "Team Fit: Pending",
                f"Outcome: {self.outcome_label_from_band(getattr(task, 'outcome_band', ''))}" if getattr(task, "outcome_band", "") else "Outcome: Pending",
            ]

        return ["No team assigned."]

    def outcome_label_from_band(self, outcome_band):
        mapping = {
            "great_success": "Great Success",
            "success": "Success",
            "partial_success": "Partial Success",
            "critical_failure": "Critical Failure",
        }
        return mapping.get(str(outcome_band), "Pending")

    def friendly_task_state(self, state_text):
        mapping = {
            TASK_STATE_PENDING: "Pending",
            TASK_STATE_TRAVELING_TO: "Traveling",
            TASK_STATE_ACTIVE: "In Progress",
            TASK_STATE_WAITING_FOR_DECISION: "Waiting For Decision",
            TASK_STATE_AWAITING_ACK: "Awaiting Review",
        }
        return mapping.get(state_text, str(state_text).replace("_", " ").title())

    def friendly_hero_state(self, state_text):
        mapping = {
            HERO_STATE_AVAILABLE: "Available",
            HERO_STATE_TRAVELING: "Traveling",
            HERO_STATE_ON_TASK: "On Mission",
            HERO_STATE_AWAITING_DECISION: "Decision Needed",
            HERO_STATE_RETURNING: "Returning",
            HERO_STATE_RESTING: "Resting",
        }
        return mapping.get(state_text, str(state_text).replace("_", " ").title())

    def generate_hints(self, task):
        hints = []
        stat_rules = get_task_stat_rules(task)

        for stat_name in ORDERED_STATS:
            rule = stat_rules.get(stat_name, {})
            mode = str(rule.get("mode", "minimum")).lower()
            stat_label = DISPLAY_STAT_LABELS.get(stat_name, stat_name.title()).lower()

            if mode == "minimum":
                target = int(rule.get("target", 0))
                if target >= 4:
                    hints.append(f"Strong {stat_label} will matter here.")
                elif target >= 2:
                    hints.append(f"Some {stat_label} could help.")
            elif mode == "range":
                hints.append(f"Balanced {stat_label} may be ideal.")
            elif mode == "maximum":
                hints.append(f"Too much {stat_label} could work against you.")

        if not hints:
            hints.append("This mission seems broadly manageable.")

        if self.scene_mode(task) == "decision":
            hints.append("The mission is paused until you choose a response.")

        return hints[:5]

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

    # -------------------------------------------------------------------------
    # Decision choice helpers
    # -------------------------------------------------------------------------

    def iter_decision_choices(self, decision_event):
        raw_choices = getattr(decision_event, "choices", []) or []
        return list(raw_choices)

    def decision_choice_id(self, choice):
        if isinstance(choice, dict):
            return str(choice.get("id", ""))
        return str(getattr(choice, "id", ""))

    def decision_choice_label(self, choice):
        if isinstance(choice, dict):
            return str(choice.get("label", "Choice"))
        return str(getattr(choice, "label", "Choice"))

    def decision_choice_description(self, choice):
        if isinstance(choice, dict):
            return str(choice.get("description", ""))
        return str(getattr(choice, "description", ""))