import pygame

from pygame_ui.ui_helpers import clamp_scroll, draw_scrollbar, truncate_text, wrap_text

from ..widgets.button import Button
from ..widgets.panel import Panel


class ManagementScene:
    RECRUIT_VISIBLE_ROWS = 4
    ROSTER_VISIBLE_ROWS = 4

    RECRUIT_ROW_SPACING = 66
    ROSTER_ROW_SPACING = 58

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

        self.mouse_pos = (0, 0)
        self.selected_hero = None
        self.selected_source = ""

        self.recruit_scroll = 0
        self.roster_scroll = 0
        self.status_message = "Guild management active."

        self.header_panel = Panel((20, 16, 1240, 86), "Guild Management")
        self.recruits_panel = Panel((20, 120, 740, 360), "Available Recruits")
        self.roster_panel = Panel((780, 120, 480, 360), "Roster")
        self.details_panel = Panel((20, 500, 1240, 190), "Selected Hero Details")

        self.recruit_row_start_y = self.recruits_panel.rect.y + 60
        self.roster_row_start_y = self.roster_panel.rect.y + 60

    def roster_capacity(self):
        return self.state.guild_upgrades.roster_capacity

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for button in self.build_all_buttons():
                if button.rect.collidepoint(event.pos):
                    button.on_click()
                    return

            self.handle_row_click(event.pos)

        elif event.type == pygame.MOUSEWHEEL:
            self.handle_mouse_wheel(event)

    def handle_mouse_wheel(self, event):
        if self.recruits_panel.rect.collidepoint(self.mouse_pos):
            self.recruit_scroll -= event.y
            self.recruit_scroll = clamp_scroll(
                self.recruit_scroll,
                len(self.state.available_contracts),
                self.RECRUIT_VISIBLE_ROWS,
            )

        elif self.roster_panel.rect.collidepoint(self.mouse_pos):
            self.roster_scroll -= event.y
            self.roster_scroll = clamp_scroll(
                self.roster_scroll,
                len(self.state.roster),
                self.ROSTER_VISIBLE_ROWS,
            )

    def update(self, mouse_pos):
        self.mouse_pos = mouse_pos

    def draw(self, screen):
        screen.fill((28, 28, 32))

        self.header_panel.draw(screen, self.title_font)
        self.recruits_panel.draw(screen, self.title_font)
        self.roster_panel.draw(screen, self.title_font)
        self.details_panel.draw(screen, self.title_font)

        self.draw_header(screen)
        self.draw_recruits(screen)
        self.draw_roster(screen)
        self.draw_details(screen)

        for button in self.build_all_buttons():
            button.update(self.mouse_pos)
            button.draw(screen, self.font)

    def draw_header(self, screen):
        stats = (
            f"Gold: {self.state.gold}g    "
            f"Campaign Year: {self.state.year}    "
            f"Roster: {len(self.state.roster)}/{self.roster_capacity()}    "
            f"Available Recruits: {len(self.state.available_contracts)}"
        )

        screen.blit(self.header_font.render(stats, True, (235, 235, 240)), (40, 56))

        if self.status_message:
            screen.blit(
                self.font.render(self.status_message, True, (180, 200, 230)),
                (760, 82),
            )

    def draw_recruits(self, screen):
        visible = self.visible_recruits()

        if not visible:
            screen.blit(
                self.font.render("No recruits available.", True, (180, 180, 190)),
                (44, self.recruit_row_start_y + 8),
            )
            self.draw_panel_scrollbar(
                screen,
                self.recruits_panel,
                self.recruit_scroll,
                len(self.state.available_contracts),
                self.RECRUIT_VISIBLE_ROWS,
            )
            return

        y = self.recruit_row_start_y
        for hero in visible:
            self.draw_recruit_row(screen, hero, y)
            y += self.RECRUIT_ROW_SPACING

        self.draw_panel_scrollbar(
            screen,
            self.recruits_panel,
            self.recruit_scroll,
            len(self.state.available_contracts),
            self.RECRUIT_VISIBLE_ROWS,
        )

    def draw_recruit_row(self, screen, hero, y):
        row_rect = self.recruit_row_rect(y)
        is_selected = hero is self.selected_hero and self.selected_source == "Recruit"
        is_hovered = row_rect.collidepoint(self.mouse_pos)

        if is_selected:
            fill_color = (58, 58, 76)
            border_color = (160, 160, 220)
            border_width = 2
        elif is_hovered:
            fill_color = (52, 52, 64)
            border_color = (110, 110, 135)
            border_width = 1
        else:
            fill_color = (42, 42, 52)
            border_color = (70, 70, 86)
            border_width = 1

        pygame.draw.rect(screen, fill_color, row_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, row_rect, border_width, border_radius=8)

        line_1 = (
            f"{hero.name} | {hero.hero_class} | Lv {hero.level} | "
            f"Age {hero.age} | Pwr {hero.combat_power()}"
        )
        line_2 = (
            f"Recruit {hero.signing_bonus}g | Expedition Cost {hero.wage_per_year}g | "
            f"Satisfaction {hero.satisfaction}/100"
        )

        screen.blit(
            self.font.render(truncate_text(line_1, self.font, 600), True, (230, 230, 240)),
            (row_rect.x + 12, row_rect.y + 8),
        )
        screen.blit(
            self.small_font.render(truncate_text(line_2, self.small_font, 600), True, (180, 180, 195)),
            (row_rect.x + 12, row_rect.y + 34),
        )

    def draw_roster(self, screen):
        visible = self.visible_roster()

        if not visible:
            screen.blit(
                self.font.render("No heroes hired yet.", True, (180, 180, 190)),
                (804, self.roster_row_start_y + 8),
            )
            self.draw_panel_scrollbar(
                screen,
                self.roster_panel,
                self.roster_scroll,
                len(self.state.roster),
                self.ROSTER_VISIBLE_ROWS,
            )
            return

        y = self.roster_row_start_y
        for hero in visible:
            self.draw_roster_row(screen, hero, y)
            y += self.ROSTER_ROW_SPACING

        self.draw_panel_scrollbar(
            screen,
            self.roster_panel,
            self.roster_scroll,
            len(self.state.roster),
            self.ROSTER_VISIBLE_ROWS,
        )

    def draw_roster_row(self, screen, hero, y):
        row_rect = self.roster_row_rect(y)
        is_selected = hero is self.selected_hero and self.selected_source == "Roster"
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

        line_1 = f"{hero.name} | {hero.hero_class} | Lv {hero.level} | Pwr {hero.combat_power()}"
        line_2 = f"Age {hero.age} | Sat {hero.satisfaction}/100 ({hero.satisfaction_label()})"

        screen.blit(
            self.font.render(truncate_text(line_1, self.font, 380), True, (210, 240, 210)),
            (row_rect.x + 12, row_rect.y + 8),
        )
        screen.blit(
            self.small_font.render(truncate_text(line_2, self.small_font, 380), True, (180, 210, 180)),
            (row_rect.x + 12, row_rect.y + 32),
        )

    def draw_details(self, screen):
        if not self.selected_hero:
            screen.blit(
                self.font.render("Select a recruit or roster hero to inspect.", True, (190, 190, 205)),
                (44, 548),
            )
            return

        hero = self.selected_hero

        left_lines = [
            f"Name: {hero.name}",
            f"Class: {hero.hero_class}    Level: {hero.level}    Age: {hero.age}",
            f"Power: {hero.combat_power()}    Health: {hero.max_health()}    Damage: {hero.damage_type()}",
            f"Recruit Cost: {hero.signing_bonus}g    Expedition Cost: {hero.wage_per_year}g",
            f"Satisfaction: {hero.satisfaction}/100 ({hero.satisfaction_label()})",
        ]

        right_lines = [
            f"Stats: Might {hero.total_stat('might')} | Agility {hero.total_stat('agility')} | Mind {hero.total_stat('mind')} | Spirit {hero.total_stat('spirit')}",
            f"Specialty: {hero.specialty}",
            f"Growth: {hero.growth_rate}",
            f"XP: {hero.xp}/{hero.xp_to_next_level()}",
            f"Injury: {hero.injured_years_remaining} year(s)" if hero.injured_years_remaining else "Injury: None",
        ]

        y = 548
        for line in left_lines:
            screen.blit(self.small_font.render(line, True, (210, 210, 220)), (44, y))
            y += 20

        y = 548
        for line in right_lines:
            for wrapped in wrap_text(line, self.small_font, 540)[:2]:
                screen.blit(self.small_font.render(wrapped, True, (210, 210, 220)), (640, y))
                y += 20

    def build_all_buttons(self):
        buttons = [
            Button((1120, 40, 80, 32), "Hub", self.on_return_to_hub),
        ]

        if self.selected_hero and self.selected_source == "Recruit":
            buttons.append(Button((1010, 635, 190, 42), "Recruit Hero", self.hire_selected_hero))

        if self.selected_hero and self.selected_source == "Roster":
            buttons.append(Button((1010, 635, 190, 42), "Release Hero", self.release_selected_hero))

        return buttons

    def handle_row_click(self, pos):
        y = self.recruit_row_start_y
        for hero in self.visible_recruits():
            if self.recruit_row_rect(y).collidepoint(pos):
                self.selected_hero = hero
                self.selected_source = "Recruit"
                self.status_message = f"Selected recruit: {hero.name}"
                return
            y += self.RECRUIT_ROW_SPACING

        y = self.roster_row_start_y
        for hero in self.visible_roster():
            if self.roster_row_rect(y).collidepoint(pos):
                self.selected_hero = hero
                self.selected_source = "Roster"
                self.status_message = f"Selected roster hero: {hero.name}"
                return
            y += self.ROSTER_ROW_SPACING

    def hire_hero(self, hero):
        if hero not in self.state.available_contracts:
            return

        if len(self.state.roster) >= self.roster_capacity():
            self.status_message = (
                f"Roster is full ({len(self.state.roster)}/{self.roster_capacity()}). "
                "Upgrade lodging to recruit more heroes."
            )
            return

        if self.state.gold < hero.signing_bonus:
            self.status_message = f"Not enough gold to recruit {hero.name}."
            return

        self.state.gold -= hero.signing_bonus
        self.state.roster.append(hero)
        self.state.available_contracts.remove(hero)

        self.recruit_scroll = clamp_scroll(
            self.recruit_scroll,
            len(self.state.available_contracts),
            self.RECRUIT_VISIBLE_ROWS,
        )

        self.selected_hero = hero
        self.selected_source = "Roster"
        self.status_message = f"Recruited {hero.name} for {hero.signing_bonus}g."

        if self.on_save_game:
            self.on_save_game()

    def hire_selected_hero(self):
        if self.selected_hero is not None and self.selected_source == "Recruit":
            self.hire_hero(self.selected_hero)

    def release_hero(self, hero):
        if hero not in self.state.roster:
            return

        self.state.roster.remove(hero)

        self.roster_scroll = clamp_scroll(
            self.roster_scroll,
            len(self.state.roster),
            self.ROSTER_VISIBLE_ROWS,
        )

        if self.selected_hero is hero:
            self.selected_hero = None
            self.selected_source = ""

        self.status_message = f"Released {hero.name} from the guild."

        if self.on_save_game:
            self.on_save_game()

    def release_selected_hero(self):
        if self.selected_hero is not None and self.selected_source == "Roster":
            self.release_hero(self.selected_hero)

    def visible_recruits(self):
        end = self.recruit_scroll + self.RECRUIT_VISIBLE_ROWS
        return self.state.available_contracts[self.recruit_scroll:end]

    def visible_roster(self):
        end = self.roster_scroll + self.ROSTER_VISIBLE_ROWS
        return self.state.roster[self.roster_scroll:end]

    def draw_panel_scrollbar(self, screen, panel, scroll, item_count, visible_count):
        draw_scrollbar(
            screen=screen,
            font=self.font,
            panel=panel,
            scroll=scroll,
            item_count=item_count,
            visible_count=visible_count,
            width=self.SCROLLBAR_WIDTH,
            margin=self.SCROLLBAR_MARGIN,
        )

    def recruit_row_rect(self, y):
        return pygame.Rect(34, y - 8, 690, 58)

    def roster_row_rect(self, y):
        return pygame.Rect(794, y - 8, 430, 50)