import pygame

from ..widgets.button import Button
from ..widgets.panel import Panel


class ManagementScene:
    CONTRACT_VISIBLE_ROWS = 4
    ROSTER_VISIBLE_ROWS = 4

    CONTRACT_ROW_SPACING = 66
    ROSTER_ROW_SPACING = 50

    SCROLLBAR_WIDTH = 8
    SCROLLBAR_MARGIN = 14

    def __init__(self, state, on_return_to_hub, on_save_game):
        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        self.font = pygame.font.SysFont(None, 22)
        self.title_font = pygame.font.SysFont(None, 28)
        self.header_font = pygame.font.SysFont(None, 30)

        self.mouse_pos = (0, 0)
        self.selected_hero = None
        self.selected_source = ""

        self.contract_scroll = 0
        self.roster_scroll = 0
        self.status_message = "Guild screen active."

        self.header_panel = Panel((20, 16, 1240, 86), "Guild Office")
        self.contracts_panel = Panel((20, 120, 740, 360), "Available Contracts")
        self.roster_panel = Panel((780, 120, 480, 360), "Roster")
        self.details_panel = Panel((20, 500, 1240, 180), "Selected Hero Details")

        self.contract_row_start_y = self.contracts_panel.rect.y + 60
        self.roster_row_start_y = self.roster_panel.rect.y + 60

    def hire_hero(self, hero):
        if hero not in self.state.available_contracts:
            return

        if self.state.gold < hero.signing_bonus:
            self.status_message = f"Not enough gold for {hero.name}"
            return

        self.state.gold -= hero.signing_bonus
        self.state.roster.append(hero)
        self.state.available_contracts.remove(hero)

        self.contract_scroll = self.clamp_scroll(
            self.contract_scroll,
            len(self.state.available_contracts),
            self.CONTRACT_VISIBLE_ROWS,
        )

        self.selected_hero = hero
        self.selected_source = "Roster"
        self.status_message = f"Hired {hero.name}"

    def hire_selected_hero(self):
        if self.selected_hero is not None and self.selected_source == "Contract":
            self.hire_hero(self.selected_hero)

    def release_hero(self, hero):
        if hero not in self.state.roster:
            return

        self.state.roster.remove(hero)

        self.roster_scroll = self.clamp_scroll(
            self.roster_scroll,
            len(self.state.roster),
            self.ROSTER_VISIBLE_ROWS,
        )

        if self.selected_hero is hero:
            self.selected_hero = None
            self.selected_source = ""

        self.status_message = f"Released {hero.name}"

    def release_selected_hero(self):
        if self.selected_hero is not None and self.selected_source == "Roster":
            self.release_hero(self.selected_hero)

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
        if self.contracts_panel.rect.collidepoint(self.mouse_pos):
            self.contract_scroll -= event.y
            self.contract_scroll = self.clamp_scroll(
                self.contract_scroll,
                len(self.state.available_contracts),
                self.CONTRACT_VISIBLE_ROWS,
            )

        elif self.roster_panel.rect.collidepoint(self.mouse_pos):
            self.roster_scroll -= event.y
            self.roster_scroll = self.clamp_scroll(
                self.roster_scroll,
                len(self.state.roster),
                self.ROSTER_VISIBLE_ROWS,
            )

    def clamp_scroll(self, value, item_count, visible_count):
        max_scroll = max(0, item_count - visible_count)
        return max(0, min(value, max_scroll))

    def update(self, mouse_pos):
        self.mouse_pos = mouse_pos

    def draw(self, screen):
        screen.fill((28, 28, 32))

        self.draw_panels(screen)
        self.draw_header(screen)
        self.draw_contracts(screen)
        self.draw_roster(screen)
        self.draw_selected_hero_details(screen)

        for button in self.build_all_buttons():
            button.update(self.mouse_pos)
            button.draw(screen, self.font)

    def draw_panels(self, screen):
        self.header_panel.draw(screen, self.title_font)
        self.contracts_panel.draw(screen, self.title_font)
        self.roster_panel.draw(screen, self.title_font)
        self.details_panel.draw(screen, self.title_font)

    def draw_header(self, screen):
        stats = (
            f"Gold: {self.state.gold}g    "
            f"Year: {self.state.year}    "
            f"Expedition: {self.state.expedition}    "
            f"Contracts: {len(self.state.available_contracts)}    "
            f"Roster: {len(self.state.roster)}"
        )

        screen.blit(self.header_font.render(stats, True, (235, 235, 240)), (40, 56))

        if self.status_message:
            screen.blit(
                self.font.render(self.status_message, True, (180, 200, 230)),
                (740, 82),
            )

    def draw_contracts(self, screen):
        y = self.contract_row_start_y

        for hero in self.visible_contracts():
            self.draw_contract_row(screen, hero, y)
            y += self.CONTRACT_ROW_SPACING

        self.draw_scrollbar(
            screen=screen,
            panel=self.contracts_panel,
            scroll=self.contract_scroll,
            item_count=len(self.state.available_contracts),
            visible_count=self.CONTRACT_VISIBLE_ROWS,
        )

    def draw_contract_row(self, screen, hero, y):
        row_rect = self.contract_row_rect(y)
        is_selected = hero is self.selected_hero
        is_hovered = row_rect.collidepoint(self.mouse_pos)

        if is_selected:
            fill_color = (58, 58, 76)
            border_color = (150, 150, 210)
            border_width = 2
        elif is_hovered:
            fill_color = (56, 56, 68)
            border_color = (110, 110, 135)
            border_width = 1
        else:
            fill_color = (48, 48, 58)
            border_color = (72, 72, 88)
            border_width = 1

        pygame.draw.rect(screen, fill_color, row_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, row_rect, border_width, border_radius=8)

        name_line = f"{hero.name} | {hero.hero_class} | {hero.specialty}"
        stat_line = (
            f"Lv {hero.level} | Pwr {hero.combat_power()} | "
            f"Sign {hero.signing_bonus}g | Wage {hero.wage_per_year}g/y"
        )

        screen.blit(self.font.render(name_line, True, (235, 235, 240)), (50, y))
        screen.blit(self.font.render(stat_line, True, (190, 190, 200)), (50, y + 20))

    def draw_roster(self, screen):
        if not self.state.roster:
            screen.blit(
                self.font.render("No heroes hired yet.", True, (180, 180, 190)),
                (800, self.roster_row_start_y),
            )
            self.draw_scrollbar(
                screen=screen,
                panel=self.roster_panel,
                scroll=self.roster_scroll,
                item_count=len(self.state.roster),
                visible_count=self.ROSTER_VISIBLE_ROWS,
            )
            return

        y = self.roster_row_start_y
        for hero in self.visible_roster():
            self.draw_roster_row(screen, hero, y)
            y += self.ROSTER_ROW_SPACING

        self.draw_scrollbar(
            screen=screen,
            panel=self.roster_panel,
            scroll=self.roster_scroll,
            item_count=len(self.state.roster),
            visible_count=self.ROSTER_VISIBLE_ROWS,
        )

    def draw_roster_row(self, screen, hero, y):
        row_rect = self.roster_row_rect(y)
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

        line = f"{hero.name} | {hero.hero_class} | Lv {hero.level} | Pwr {hero.combat_power()}"
        screen.blit(self.font.render(line, True, (210, 240, 210)), (810, y + 2))

    def draw_selected_hero_details(self, screen):
        if self.selected_hero is None:
            screen.blit(
                self.font.render("Click a contract or roster hero to inspect them.", True, (180, 180, 190)),
                (40, 550),
            )
            return

        hero = self.selected_hero

        stat_text = (
            f"Might {hero.total_stat('might')}    "
            f"Agility {hero.total_stat('agility')}    "
            f"Mind {hero.total_stat('mind')}    "
            f"Spirit {hero.total_stat('spirit')}"
        )

        lines = [
            f"{hero.name} ({self.selected_source})",
            f"Class: {hero.hero_class}    Specialty: {hero.specialty}    Growth: {hero.growth_rate}",
            f"Level: {hero.level}    XP: {hero.xp}/{hero.xp_to_next_level()}    Power: {hero.combat_power()}",
            f"Age: {hero.age}    Contract: {hero.contract_years}y    Signing: {hero.signing_bonus}g    Wage: {hero.wage_per_year}g/y",
            stat_text,
        ]

        y = 540
        for index, line in enumerate(lines):
            color = (245, 245, 250) if index == 0 else (200, 200, 210)
            screen.blit(self.font.render(line, True, color), (40, y))
            y += 24

    def draw_scrollbar(self, screen, panel, scroll, item_count, visible_count):
        track_rect = self.scrollbar_track_rect(panel)

        pygame.draw.rect(screen, (44, 44, 54), track_rect, border_radius=4)

        if item_count <= visible_count:
            pygame.draw.rect(screen, (72, 72, 88), track_rect, border_radius=4)
            return

        max_scroll = max(1, item_count - visible_count)

        thumb_height = max(
            28,
            int(track_rect.height * (visible_count / item_count)),
        )

        scroll_ratio = scroll / max_scroll
        thumb_y = track_rect.y + int((track_rect.height - thumb_height) * scroll_ratio)

        thumb_rect = pygame.Rect(
            track_rect.x,
            thumb_y,
            track_rect.width,
            thumb_height,
        )

        pygame.draw.rect(screen, (120, 120, 150), thumb_rect, border_radius=4)

        hint = f"{scroll + 1}-{min(scroll + visible_count, item_count)} of {item_count}"
        screen.blit(
            self.font.render(hint, True, (160, 160, 175)),
            (panel.rect.right - 118, panel.rect.bottom - 28),
        )

    def scrollbar_track_rect(self, panel):
        return pygame.Rect(
            panel.rect.right - self.SCROLLBAR_MARGIN - self.SCROLLBAR_WIDTH,
            panel.rect.y + 50,
            self.SCROLLBAR_WIDTH,
            panel.rect.height - 82,
        )

    def build_all_buttons(self):
        buttons = []
        buttons.extend(self.build_header_buttons())
        buttons.extend(self.build_contract_buttons())
        buttons.extend(self.build_detail_buttons())
        return buttons

    def build_header_buttons(self):
        return [
            Button((1120, 40, 80, 32), "Hub", self.on_return_to_hub),
        ]

    def build_contract_buttons(self):
        buttons = []

        y = self.contract_row_start_y
        for hero in self.visible_contracts():
            buttons.append(
                Button(
                    (595, y + 3, 105, 28),
                    "Hire",
                    lambda h=hero: self.hire_hero(h),
                )
            )
            y += self.CONTRACT_ROW_SPACING

        return buttons

    def build_detail_buttons(self):
        buttons = []

        if self.selected_hero is None:
            return buttons

        if self.selected_source == "Contract":
            buttons.append(Button((1010, 610, 190, 42), "Hire Selected", self.hire_selected_hero))
        elif self.selected_source == "Roster":
            buttons.append(Button((1010, 610, 190, 42), "Release Selected", self.release_selected_hero))

        return buttons

    def handle_row_click(self, pos):
        y = self.contract_row_start_y
        for hero in self.visible_contracts():
            if self.contract_row_rect(y).collidepoint(pos):
                self.selected_hero = hero
                self.selected_source = "Contract"
                return
            y += self.CONTRACT_ROW_SPACING

        y = self.roster_row_start_y
        for hero in self.visible_roster():
            if self.roster_row_rect(y).collidepoint(pos):
                self.selected_hero = hero
                self.selected_source = "Roster"
                return
            y += self.ROSTER_ROW_SPACING

    def visible_contracts(self):
        end = self.contract_scroll + self.CONTRACT_VISIBLE_ROWS
        return self.state.available_contracts[self.contract_scroll:end]

    def visible_roster(self):
        end = self.roster_scroll + self.ROSTER_VISIBLE_ROWS
        return self.state.roster[self.roster_scroll:end]

    def contract_row_rect(self, y):
        return pygame.Rect(36, y - 10, 684, 54)

    def roster_row_rect(self, y):
        return pygame.Rect(796, y - 8, 420, 40)