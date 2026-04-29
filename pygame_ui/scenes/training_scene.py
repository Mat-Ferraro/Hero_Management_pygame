import pygame

from pygame_ui.ui_helpers import clamp_scroll, draw_scrollbar, truncate_text, wrap_text
from systems.training_system import can_train_hero, train_hero, training_cost, training_xp

from ..widgets.button import Button
from ..widgets.panel import Panel


class TrainingScene:
    HERO_VISIBLE_ROWS = 6
    LOG_VISIBLE_ROWS = 4

    HERO_ROW_SPACING = 58
    LOG_ROW_SPACING = 22

    SCROLLBAR_WIDTH = 8
    SCROLLBAR_MARGIN = 14

    def __init__(self, state, on_return_to_hub, on_save_game):
        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        self.font = pygame.font.SysFont(None, 22)
        self.small_font = pygame.font.SysFont(None, 20)
        self.title_font = pygame.font.SysFont(None, 28)
        self.header_font = pygame.font.SysFont(None, 30)
        self.stat_font = pygame.font.SysFont(None, 26)

        self.mouse_pos = (0, 0)
        self.status_message = "Select a hero to train."

        self.selected_hero = None
        self.hero_scroll = 0
        self.log_scroll = 0
        self.log_lines = ["Training Hall opened."]

        self.header_panel = Panel((20, 16, 1240, 86), "Training Hall")
        self.heroes_panel = Panel((20, 120, 720, 430), "Roster")
        self.details_panel = Panel((760, 120, 500, 260), "Training Details")
        self.log_panel = Panel((760, 400, 500, 150), "Training Log")
        self.footer_panel = Panel((20, 570, 1240, 135), "Career Notes")

        self.hero_row_start_y = self.heroes_panel.rect.y + 60

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for button in self.build_buttons():
                if button.rect.collidepoint(event.pos):
                    button.on_click()
                    return

            self.handle_row_click(event.pos)

        elif event.type == pygame.MOUSEWHEEL:
            if self.heroes_panel.rect.collidepoint(self.mouse_pos):
                self.hero_scroll -= event.y
                self.hero_scroll = clamp_scroll(
                    self.hero_scroll,
                    len(self.state.roster),
                    self.HERO_VISIBLE_ROWS,
                )

            elif self.log_panel.rect.collidepoint(self.mouse_pos):
                self.log_scroll -= event.y
                self.log_scroll = clamp_scroll(
                    self.log_scroll,
                    len(self.log_lines),
                    self.LOG_VISIBLE_ROWS,
                )

    def update(self, mouse_pos):
        self.mouse_pos = mouse_pos

    def draw(self, screen):
        screen.fill((28, 28, 32))

        self.header_panel.draw(screen, self.title_font)
        self.heroes_panel.draw(screen, self.title_font)
        self.details_panel.draw(screen, self.title_font)
        self.log_panel.draw(screen, self.title_font)
        self.footer_panel.draw(screen, self.title_font)

        self.draw_header(screen)
        self.draw_heroes(screen)
        self.draw_details(screen)
        self.draw_log(screen)
        self.draw_footer(screen)

        for button in self.build_buttons():
            button.update(self.mouse_pos)
            button.draw(screen, self.font)

    def draw_header(self, screen):
        level = self.state.guild_upgrades.training_hall_level
        cost = training_cost(level)
        xp = training_xp(level)

        stats = (
            f"Gold: {self.state.gold}g    "
            f"Training Hall Lv {level}    "
            f"Base Training Cost: {cost}g    "
            f"Training XP: {xp}"
        )

        screen.blit(self.header_font.render(stats, True, (235, 235, 240)), (40, 56))

        if self.status_message:
            screen.blit(
                self.font.render(self.status_message, True, (180, 200, 230)),
                (760, 82),
            )

    def draw_heroes(self, screen):
        visible = self.visible_heroes()

        if not visible:
            screen.blit(
                self.font.render("No heroes available.", True, (180, 180, 190)),
                (44, self.hero_row_start_y + 8),
            )
            return

        y = self.hero_row_start_y
        for hero in visible:
            self.draw_hero_row(screen, hero, y)
            y += self.HERO_ROW_SPACING

        draw_scrollbar(
            screen=screen,
            font=self.font,
            panel=self.heroes_panel,
            scroll=self.hero_scroll,
            item_count=len(self.state.roster),
            visible_count=self.HERO_VISIBLE_ROWS,
            width=self.SCROLLBAR_WIDTH,
            margin=self.SCROLLBAR_MARGIN,
        )

    def draw_hero_row(self, screen, hero, y):
        row_rect = self.hero_row_rect(y)
        is_selected = hero is self.selected_hero
        is_hovered = row_rect.collidepoint(self.mouse_pos)

        if is_selected:
            fill_color = (52, 70, 56)
            border_color = (150, 220, 160)
            border_width = 2
        elif is_hovered:
            fill_color = (48, 64, 52)
            border_color = (100, 150, 110)
            border_width = 1
        else:
            fill_color = (42, 54, 44)
            border_color = (72, 96, 76)
            border_width = 1

        pygame.draw.rect(screen, fill_color, row_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, row_rect, border_width, border_radius=8)

        allowed, reason = can_train_hero(hero)
        status = "Trainable" if allowed else reason

        subclass = hero.subclass or "Base"
        line_1 = (
            f"{hero.name} | {hero.hero_class}/{subclass} | "
            f"Lv {hero.level} | Age {hero.age} ({hero.career_stage()})"
        )
        line_2 = (
            f"XP {hero.xp}/{hero.xp_to_next_level()} | "
            f"Pwr {hero.combat_power()} | Mentor {hero.mentorship_value()} | {status}"
        )

        screen.blit(
            self.font.render(truncate_text(line_1, self.font, 610), True, (210, 240, 210)),
            (row_rect.x + 12, row_rect.y + 8),
        )
        screen.blit(
            self.small_font.render(truncate_text(line_2, self.small_font, 610), True, (180, 210, 180)),
            (row_rect.x + 12, row_rect.y + 32),
        )

    def draw_details(self, screen):
        panel = self.details_panel.rect

        level = self.state.guild_upgrades.training_hall_level
        cost = training_cost(level)
        xp = training_xp(level)

        # Smaller badge (less right padding usage)
        self.draw_training_price_badge(screen, panel, cost, xp)

        text_x = panel.x + 30
        text_width = panel.width - 200  # leave room for badge

        if self.selected_hero is None:
            lines = wrap_text(
                "Select a hero to inspect training results.",
                self.small_font,
                text_width,
            )

            y = panel.y + 70
            for line in lines:
                screen.blit(self.small_font.render(line, True, (190, 190, 205)), (text_x, y))
                y += 22

            return

        hero = self.selected_hero
        allowed, reason = can_train_hero(hero)

        lines = [
            f"Hero: {hero.name}",
            f"Class: {hero.hero_class}    Subclass: {hero.subclass or 'None'}",
            f"Ability: {hero.special_ability or 'None'}",
            f"Level: {hero.level}    XP: {hero.xp}/{hero.xp_to_next_level()}",
            f"Status: {'Ready' if allowed else reason}",
        ]

        y = panel.y + 60
        for line in lines:
            for wrapped in wrap_text(line, self.small_font, text_width):
                screen.blit(self.small_font.render(wrapped, True, (210, 210, 220)), (text_x, y))
                y += 20

    def draw_training_price_badge(self, screen, panel, cost, xp):
        badge_rect = pygame.Rect(panel.right - 160, panel.y + 50, 130, 70)

        pygame.draw.rect(screen, (48, 48, 62), badge_rect, border_radius=8)
        pygame.draw.rect(screen, (150, 150, 190), badge_rect, 2, border_radius=8)

        screen.blit(self.small_font.render("Cost", True, (190, 190, 205)),
                    (badge_rect.x + 14, badge_rect.y + 8))

        screen.blit(self.stat_font.render(f"{cost}g", True, (245, 235, 210)),
                    (badge_rect.x + 14, badge_rect.y + 26))

        screen.blit(self.small_font.render(f"+{xp} XP", True, (190, 220, 190)),
                    (badge_rect.x + 14, badge_rect.y + 48))

    def draw_log(self, screen):
        panel = self.log_panel.rect
        visible = self.log_lines[self.log_scroll:self.log_scroll + self.LOG_VISIBLE_ROWS]

        y = panel.y + 50
        max_text_width = panel.width - 80

        for line in visible:
            screen.blit(
                self.small_font.render(
                    truncate_text(line, self.small_font, max_text_width),
                    True,
                    (210, 210, 220),
                ),
                (panel.x + 30, y),
            )
            y += self.LOG_ROW_SPACING

        draw_scrollbar(
            screen=screen,
            font=self.font,
            panel=self.log_panel,
            scroll=self.log_scroll,
            item_count=len(self.log_lines),
            visible_count=self.LOG_VISIBLE_ROWS,
            width=self.SCROLLBAR_WIDTH,
            margin=self.SCROLLBAR_MARGIN,
        )

    def draw_footer(self, screen):
        lines = [
            "Training is safe but costs gold. Expeditions remain the fastest way to grow heroes.",
            "Future Training Hall upgrades will unlock subclass choices and special abilities.",
            "Older heroes may lose raw power, but their mentorship and learned abilities can remain valuable.",
        ]

        y = 614
        for line in lines:
            screen.blit(self.small_font.render(line, True, (200, 200, 215)), (44, y))
            y += 24

    def build_buttons(self):
        buttons = [
            Button((1120, 40, 80, 32), "Hub", self.on_return_to_hub),
        ]

        if self.selected_hero is not None:
            buttons.append(Button((1010, 318, 190, 42), "Train Hero", self.train_selected_hero))

        return buttons

    def handle_row_click(self, pos):
        y = self.hero_row_start_y
        for hero in self.visible_heroes():
            if self.hero_row_rect(y).collidepoint(pos):
                self.selected_hero = hero
                self.status_message = f"Selected hero: {hero.name}"
                return
            y += self.HERO_ROW_SPACING

    def train_selected_hero(self):
        if self.selected_hero is None:
            self.status_message = "Select a hero first."
            return

        messages = train_hero(self.state, self.selected_hero)
        self.log_lines.extend(messages)
        self.status_message = messages[-1] if messages else "Training complete."

        self.log_scroll = clamp_scroll(
            max(0, len(self.log_lines) - self.LOG_VISIBLE_ROWS),
            len(self.log_lines),
            self.LOG_VISIBLE_ROWS,
        )

        if self.on_save_game:
            self.on_save_game()

    def visible_heroes(self):
        end = self.hero_scroll + self.HERO_VISIBLE_ROWS
        return self.state.roster[self.hero_scroll:end]

    def hero_row_rect(self, y):
        return pygame.Rect(34, y - 8, 660, 50)