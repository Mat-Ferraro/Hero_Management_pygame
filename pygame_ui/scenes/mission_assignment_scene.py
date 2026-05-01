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
from systems.campaign.campaign_runtime import acknowledge_task_results, resolve_open_decision
from systems.campaign.task_dispatch import assign_heroes_to_task, find_task
from systems.campaign.task_resolution import (
    calculate_task_success,
    combined_party_dispatch_stats,
    format_dispatch_stats,
    hero_dispatch_stats,
)

DISPLAY_STAT_LABELS = {
    "might": "Might",
    "guard": "Guard",
    "wit": "Wit",
    "presence": "Presence",
    "swift": "Swift",
}


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

        task = self.current_task()
        if task is not None and task.state != TASK_STATE_PENDING:
            self.staged_team_names = list(task.assigned_heroes)

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

    def handle_event(self, event):
        if self.handle_buttons_click(event, self.build_buttons()):
            return

        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", None) == 1:
            self.handle_slot_click(event.pos)
            self.handle_hero_card_click(event.pos)

    def update(self, mouse_pos):
        super().update(mouse_pos)

    def draw(self, screen):
        self.clear_screen(screen)

        task = self.current_task()
        if task is None:
            screen.blit(self.title_font.render("Mission not found.", True, theme.TEXT_PRIMARY), (60, 60))
            return

        self.draw_header(screen, task)
        self.draw_layout(screen, task)
        self.update_and_draw_buttons(screen, self.build_buttons())

    def draw_header(self, screen, task):
        pygame.draw.rect(screen, (34, 34, 42), (30, 20, 1820, 78), border_radius=12)
        pygame.draw.rect(screen, (92, 96, 112), (30, 20, 1820, 78), 2, border_radius=12)

        title = self.title_font.render(task.task_type, True, theme.TEXT_PRIMARY)
        screen.blit(title, (50, 36))

        state_text = f"State: {task.state.replace('_', ' ').title()}"
        screen.blit(self.font.render(state_text, True, theme.TEXT_SECONDARY), (420, 42))

        if self.status_message:
            screen.blit(self.font.render(self.status_message, True, theme.TEXT_PRIMARY), (740, 42))

    def draw_layout(self, screen, task):
        left_rect = pygame.Rect(40, 120, 520, 520)
        center_rect = pygame.Rect(580, 120, 560, 520)
        right_rect = pygame.Rect(1160, 120, 650, 520)
        footer_rect = pygame.Rect(40, 670, 1770, 250)

        self.draw_panel(screen, left_rect, "Mission Details")
        self.draw_panel(screen, center_rect, "Team Assignment")
        self.draw_panel(screen, right_rect, "Mission Hints")
        self.draw_panel(screen, footer_rect, "Available Heroes")

        self.draw_mission_details(screen, task, left_rect)
        self.draw_team_assignment(screen, task, center_rect)
        self.draw_mission_hints(screen, task, right_rect)
        self.draw_available_heroes(screen, task, footer_rect)

    def draw_panel(self, screen, rect, title):
        pygame.draw.rect(screen, (34, 34, 42), rect, border_radius=12)
        pygame.draw.rect(screen, (92, 96, 112), rect, 2, border_radius=12)
        text = self.font.render(title, True, theme.TEXT_PRIMARY)
        screen.blit(text, (rect.x + 16, rect.y + 12))

    def draw_mission_details(self, screen, task, rect):
        y = rect.y + 56

        rows = [
            f"Task: {task.task_type}",
            f"Difficulty: {task.difficulty}",
            f"Duration: {task.task_duration:.1f}s",
            f"Reward: {task.reward_gold_min}-{task.reward_gold_max}g / {task.reward_xp} XP",
            f"Max Heroes: {task.max_heroes}",
            f"Preferred Classes: {', '.join(task.preferred_classes) or 'Any'}",
        ]

        for row in rows:
            screen.blit(self.font.render(row, True, theme.TEXT_PRIMARY), (rect.x + 20, y))
            y += 28

        y += 14
        story_lines = self.mission_story_lines(task)
        for line in story_lines:
            for wrapped in wrap_text(line, self.small_font, rect.width - 40):
                screen.blit(self.small_font.render(wrapped, True, theme.TEXT_SECONDARY), (rect.x + 20, y))
                y += 20
            y += 6

        decision_event = self.current_decision_event()
        if decision_event is not None:
            y += 10
            screen.blit(self.font.render("Decision Required", True, theme.TEXT_PRIMARY), (rect.x + 20, y))
            y += 30

            for wrapped in wrap_text(decision_event.description, self.small_font, rect.width - 40):
                screen.blit(self.small_font.render(wrapped, True, theme.TEXT_SECONDARY), (rect.x + 20, y))
                y += 20

        if task.state == TASK_STATE_AWAITING_ACK:
            y += 8
            screen.blit(self.font.render("Mission Result", True, theme.TEXT_PRIMARY), (rect.x + 20, y))
            y += 30
            for wrapped in wrap_text(task.outcome_summary or "Mission complete.", self.small_font, rect.width - 40):
                screen.blit(self.small_font.render(wrapped, True, theme.TEXT_SECONDARY), (rect.x + 20, y))
                y += 20

    def draw_team_assignment(self, screen, task, rect):
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
            pygame.draw.rect(screen, (48, 48, 60), slot_rect, border_radius=8)
            pygame.draw.rect(screen, (98, 102, 120), slot_rect, 1, border_radius=8)

            if index < len(self.staged_team_names):
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
                StatusChip(
                    rect=(slot_rect.x + 8, slot_rect.bottom - 26, slot_rect.width - 16, 18),
                    text="Assigned",
                    style="info",
                ).draw(screen, self.small_font)
            else:
                placeholder = self.small_font.render("Empty Slot", True, theme.TEXT_MUTED)
                screen.blit(placeholder, (slot_rect.x + 8, slot_rect.y + 20))

        stats_y = rect.y + 180
        screen.blit(self.font.render("Team Strength", True, theme.TEXT_PRIMARY), (rect.x + 20, stats_y))
        stats_y += 36

        for stat_key in ["might", "guard", "wit", "presence", "swift"]:
            self.draw_stat_row(
                screen,
                x=rect.x + 20,
                y=stats_y,
                label=DISPLAY_STAT_LABELS[stat_key],
                value=int(staged_stats.get(stat_key, 0)),
                width=360,
            )
            stats_y += 40

        preview_y = rect.y + 395
        if task.state == TASK_STATE_PENDING and staged_heroes:
            result = calculate_task_success(task, staged_heroes)
            preview_rows = [
                f"Coverage: {result['raw_coverage_ratio']:.0%}",
                f"Success: {result['success_chance']:.0%}",
                f"Expected Outcome: {result['outcome_band'].replace('_', ' ').title()}",
            ]
        elif task.state != TASK_STATE_PENDING and task.assigned_heroes:
            preview_rows = [
                f"Assigned: {', '.join(task.assigned_heroes)}",
                f"Coverage: {task.coverage_ratio:.0%}" if task.coverage_ratio > 0 else "Coverage: Pending",
                f"Outcome: {task.outcome_band.replace('_', ' ').title()}" if task.outcome_band else "Outcome: Pending",
            ]
        else:
            preview_rows = ["Select heroes to preview this team."]

        for row in preview_rows:
            screen.blit(self.small_font.render(row, True, theme.TEXT_SECONDARY), (rect.x + 20, preview_y))
            preview_y += 22

        summary_y = rect.y + 470
        summary_text = format_dispatch_stats(staged_stats)
        screen.blit(self.small_font.render(summary_text, True, theme.TEXT_PRIMARY), (rect.x + 20, summary_y))

    def draw_mission_hints(self, screen, task, rect):
        y = rect.y + 56
        for hint in self.generate_hints(task):
            for wrapped in wrap_text(f"- {hint}", self.font, rect.width - 40):
                screen.blit(self.font.render(wrapped, True, theme.TEXT_PRIMARY), (rect.x + 20, y))
                y += 26
            y += 10

    def draw_available_heroes(self, screen, task, rect):
        visible = self.state.roster[:10]
        card_rects = self.hero_card_rects(rect, len(visible))

        for hero, card_rect in zip(visible, card_rects):
            hero_state = self.runtime.hero_states.get(hero.name) if self.runtime else None
            state_text = hero_state.state if hero_state else "unknown"
            is_staged = hero.name in self.staged_team_names

            fill = (52, 52, 62)
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

            pygame.draw.rect(screen, fill, card_rect, border_radius=10)
            pygame.draw.rect(screen, (98, 102, 120), card_rect, 1, border_radius=10)

            screen.blit(
                self.small_font.render(
                    truncate_text(hero.name, self.small_font, card_rect.width - 12),
                    True,
                    theme.TEXT_PRIMARY,
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

            chip_text = "Assigned Here" if is_staged else state_text.replace("_", " ")
            chip_style = "info" if is_staged else self.hero_state_chip_style(state_text)
            StatusChip(
                rect=(card_rect.x + 8, card_rect.bottom - 24, card_rect.width - 16, 18),
                text=chip_text,
                style=chip_style,
            ).draw(screen, self.small_font)

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

        decision_event = self.current_decision_event()
        if decision_event is not None:
            choice_width = 220
            choice_gap = 18
            choices = decision_event.choices[:3]
            total_width = (len(choices) * choice_width) + (max(0, len(choices) - 1) * choice_gap)
            start_x = 1920 - right_padding - total_width
            for index, choice in enumerate(choices):
                choice_id = choice.get("id", "")
                label = choice.get("label", "Choose")
                buttons.append(
                    Button(
                        (start_x + index * (choice_width + choice_gap), button_y, choice_width, button_height),
                        label,
                        lambda cid=choice_id: self.resolve_decision_choice(cid),
                    )
                )
            return buttons

        if task.state == TASK_STATE_PENDING:
            buttons.append(Button((button_x, button_y, button_width, button_height), "Dispatch", self.dispatch_staged_team))
        elif task.state == TASK_STATE_AWAITING_ACK:
            buttons.append(Button((button_x, button_y, button_width, button_height), "Return Heroes", self.acknowledge_results))

        return buttons

    def handle_slot_click(self, pos):
        task = self.current_task()
        if task is None or task.state != TASK_STATE_PENDING:
            return

        for index, rect in enumerate(self.slot_rects(pygame.Rect(580, 120, 560, 520), task.max_heroes)):
            if rect.collidepoint(pos):
                if index < len(self.staged_team_names):
                    removed = self.staged_team_names.pop(index)
                    self.status_message = f"Removed {removed}."
                return

    def handle_hero_card_click(self, pos):
        task = self.current_task()
        if task is None or task.state != TASK_STATE_PENDING:
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

        if task.state != TASK_STATE_PENDING:
            self.status_message = "This mission is no longer pending."
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

        success, message = acknowledge_task_results(
            runtime=self.runtime,
            task_id=task.task_id,
            now=self.runtime.elapsed_time,
        )
        self.status_message = message

        if success:
            if self.on_save_game:
                self.on_save_game()
            self.on_return_to_campaign("Heroes returning from mission.")

    def resolve_decision_choice(self, choice_id):
        message = resolve_open_decision(self.runtime, choice_id)
        self.status_message = message

        if self.on_save_game:
            self.on_save_game()

        self.on_return_to_campaign("Decision resolved.")

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

    def return_to_campaign(self):
        if self.on_save_game:
            self.on_save_game()
        self.on_return_to_campaign("Returned to campaign.")

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

    def generate_hints(self, task):
        hints = []
        required = task.required_stats

        if required.get("swift", 0) >= 4:
            hints.append("A swift response may matter here.")
        elif required.get("swift", 0) >= 2:
            hints.append("Mobility could improve your odds.")

        if required.get("guard", 0) >= 4:
            hints.append("Survival and defense look important.")
        elif required.get("guard", 0) >= 2:
            hints.append("A sturdy hero may be useful.")

        if required.get("wit", 0) >= 4:
            hints.append("Careful planning could turn the tide.")
        elif required.get("wit", 0) >= 2:
            hints.append("A sharp mind may help.")

        if required.get("presence", 0) >= 4:
            hints.append("A commanding presence may be valuable.")
        elif required.get("presence", 0) >= 2:
            hints.append("Social skill may influence the outcome.")

        if required.get("might", 0) >= 4:
            hints.append("Raw force may be required.")
        elif required.get("might", 0) >= 2:
            hints.append("Some physical strength could help.")

        if not hints:
            hints.append("This mission seems broadly manageable.")
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