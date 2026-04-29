import pygame

from ..widgets.button import Button
from ..widgets.panel import Panel


class ExpeditionScene:
    PARTY_LIMIT = 4

    ROSTER_VISIBLE_ROWS = 6
    DUNGEON_VISIBLE_ROWS = 4
    PARTY_VISIBLE_ROWS = 4

    ROSTER_ROW_SPACING = 48
    DUNGEON_ROW_SPACING = 84
    PARTY_ROW_SPACING = 48

    SCROLLBAR_WIDTH = 8
    SCROLLBAR_MARGIN = 14

    def __init__(self, state, on_return_to_hub, on_start_expedition):
        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_start_expedition = on_start_expedition

        self.font = pygame.font.SysFont(None, 22)
        self.title_font = pygame.font.SysFont(None, 28)
        self.header_font = pygame.font.SysFont(None, 30)

        self.mouse_pos = (0, 0)
        self.status_message = "Choose heroes and a dungeon."

        self.selected_party = []
        self.selected_dungeon = None

        self.roster_scroll = 0
        self.party_scroll = 0
        self.dungeon_scroll = 0

        self.header_panel = Panel((20, 16, 1240, 86), "Expedition Prep")
        self.roster_panel = Panel((20, 120, 520, 410), "Available Heroes")
        self.party_panel = Panel((560, 120, 320, 410), "Party")
        self.dungeon_panel = Panel((900, 120, 360, 410), "Dungeons")
        self.details_panel = Panel((20, 548, 1240, 160), "Expedition Details")

        self.roster_row_start_y = self.roster_panel.rect.y + 60
        self.party_row_start_y = self.party_panel.rect.y + 60
        self.dungeon_row_start_y = self.dungeon_panel.rect.y + 60

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
        if self.roster_panel.rect.collidepoint(self.mouse_pos):
            self.roster_scroll -= event.y
            self.roster_scroll = self.clamp_scroll(self.roster_scroll, len(self.available_roster()), self.ROSTER_VISIBLE_ROWS)

        elif self.party_panel.rect.collidepoint(self.mouse_pos):
            self.party_scroll -= event.y
            self.party_scroll = self.clamp_scroll(self.party_scroll, len(self.selected_party), self.PARTY_VISIBLE_ROWS)

        elif self.dungeon_panel.rect.collidepoint(self.mouse_pos):
            self.dungeon_scroll -= event.y
            self.dungeon_scroll = self.clamp_scroll(self.dungeon_scroll, len(self.state.dungeons), self.DUNGEON_VISIBLE_ROWS)

    def update(self, mouse_pos):
        self.mouse_pos = mouse_pos

    def draw(self, screen):
        screen.fill((28, 28, 32))

        self.draw_panels(screen)
        self.draw_header(screen)
        self.draw_roster(screen)
        self.draw_party(screen)
        self.draw_dungeons(screen)
        self.draw_details(screen)

        for button in self.build_all_buttons():
            button.update(self.mouse_pos)
            button.draw(screen, self.font)

    def draw_panels(self, screen):
        self.header_panel.draw(screen, self.title_font)
        self.roster_panel.draw(screen, self.title_font)
        self.party_panel.draw(screen, self.title_font)
        self.dungeon_panel.draw(screen, self.title_font)
        self.details_panel.draw(screen, self.title_font)

    def draw_header(self, screen):
        stats = (
            f"Gold: {self.state.gold}g    "
            f"Year: {self.state.year}    "
            f"Expedition: {self.state.expedition}    "
            f"Party: {len(self.selected_party)}/{self.PARTY_LIMIT}"
        )

        screen.blit(self.header_font.render(stats, True, (235, 235, 240)), (40, 56))

        if self.status_message:
            screen.blit(self.font.render(self.status_message, True, (180, 200, 230)), (740, 82))

    def draw_roster(self, screen):
        visible = self.visible_roster()

        if not visible:
            screen.blit(self.font.render("No available heroes.", True, (180, 180, 190)), (40, self.roster_row_start_y + 8))
            self.draw_scrollbar(screen, self.roster_panel, self.roster_scroll, len(self.available_roster()), self.ROSTER_VISIBLE_ROWS)
            return

        y = self.roster_row_start_y
        for hero in visible:
            self.draw_roster_row(screen, hero, y)
            y += self.ROSTER_ROW_SPACING

        self.draw_scrollbar(screen, self.roster_panel, self.roster_scroll, len(self.available_roster()), self.ROSTER_VISIBLE_ROWS)

    def draw_roster_row(self, screen, hero, y):
        row_rect = self.roster_row_rect(y)
        is_hovered = row_rect.collidepoint(self.mouse_pos)

        fill_color = (50, 50, 62) if is_hovered else (42, 42, 52)
        border_color = (110, 110, 135) if is_hovered else (70, 70, 86)

        pygame.draw.rect(screen, fill_color, row_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, row_rect, 1, border_radius=8)

        line = f"{hero.name} | {hero.hero_class} | Lv {hero.level} | Pwr {hero.combat_power()}"
        rendered_line = self.truncate_text(line, self.font, 365)
        screen.blit(self.font.render(rendered_line, True, (225, 225, 235)), (38, row_rect.y + 11))

    def draw_party(self, screen):
        visible = self.visible_party()

        if not visible:
            screen.blit(self.font.render("No party selected.", True, (180, 180, 190)), (580, self.party_row_start_y + 8))
            self.draw_scrollbar(screen, self.party_panel, self.party_scroll, len(self.selected_party), self.PARTY_VISIBLE_ROWS)
            return

        y = self.party_row_start_y
        for hero in visible:
            self.draw_party_row(screen, hero, y)
            y += self.PARTY_ROW_SPACING

        self.draw_scrollbar(screen, self.party_panel, self.party_scroll, len(self.selected_party), self.PARTY_VISIBLE_ROWS)

    def draw_party_row(self, screen, hero, y):
        row_rect = self.party_row_rect(y)
        is_hovered = row_rect.collidepoint(self.mouse_pos)

        fill_color = (52, 70, 56) if is_hovered else (42, 54, 44)
        border_color = (120, 180, 130) if is_hovered else (72, 96, 76)

        pygame.draw.rect(screen, fill_color, row_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, row_rect, 1, border_radius=8)

        line = f"{hero.name} | {hero.hero_class}"
        rendered_line = self.truncate_text(line, self.font, 176)
        screen.blit(self.font.render(rendered_line, True, (210, 240, 210)), (602, row_rect.y + 11))

    def draw_dungeons(self, screen):
        visible = self.visible_dungeons()

        y = self.dungeon_row_start_y
        for dungeon in visible:
            self.draw_dungeon_row(screen, dungeon, y)
            y += self.DUNGEON_ROW_SPACING

        self.draw_scrollbar(screen, self.dungeon_panel, self.dungeon_scroll, len(self.state.dungeons), self.DUNGEON_VISIBLE_ROWS)

    def draw_dungeon_row(self, screen, dungeon, y):
        row_rect = self.dungeon_row_rect(y)
        is_selected = dungeon is self.selected_dungeon
        is_hovered = row_rect.collidepoint(self.mouse_pos)

        if is_selected:
            fill_color = (70, 58, 48)
            border_color = (220, 170, 100)
            border_width = 2
        elif is_hovered:
            fill_color = (60, 52, 44)
            border_color = (150, 120, 85)
            border_width = 1
        else:
            fill_color = (48, 42, 38)
            border_color = (88, 76, 66)
            border_width = 1

        pygame.draw.rect(screen, fill_color, row_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, row_rect, border_width, border_radius=8)

        line_1 = self.truncate_text(dungeon.name, self.font, 255)
        line_2 = f"Diff {dungeon.difficulty} | {dungeon.enemy_type} | {dungeon.years_to_complete}y"
        line_3 = f"Loot {dungeon.loot_min}-{dungeon.loot_max}g"

        screen.blit(self.font.render(line_1, True, (240, 230, 210)), (954, row_rect.y + 10))
        screen.blit(self.font.render(line_2, True, (205, 195, 180)), (954, row_rect.y + 34))
        screen.blit(self.font.render(line_3, True, (190, 180, 165)), (954, row_rect.y + 58))

    def draw_details(self, screen):
        party_power = sum(hero.combat_power() for hero in self.selected_party)

        lines = [
            f"Party Power: {party_power}",
            f"Selected Heroes: {', '.join(hero.name for hero in self.selected_party) or 'None'}",
        ]

        if self.selected_dungeon:
            dungeon = self.selected_dungeon
            lines.extend(
                [
                    f"Dungeon: {dungeon.name}",
                    f"Enemy: {dungeon.enemy_type}    Enemy Power: {dungeon.enemy_power}    Difficulty: {dungeon.difficulty}",
                    f"Expected Reward: {dungeon.loot_min}-{dungeon.loot_max}g    XP: {dungeon.xp_reward}",
                ]
            )
        else:
            lines.append("Dungeon: None selected")

        y = 590
        for line in lines[:5]:
            screen.blit(self.font.render(line, True, (210, 210, 220)), (40, y))
            y += 22

    def build_all_buttons(self):
        buttons = []
        buttons.extend(self.build_header_buttons())
        buttons.extend(self.build_roster_buttons())
        buttons.extend(self.build_party_buttons())
        buttons.extend(self.build_detail_buttons())
        return buttons

    def build_header_buttons(self):
        return [Button((1120, 40, 80, 32), "Hub", self.on_return_to_hub)]

    def build_roster_buttons(self):
        buttons = []

        y = self.roster_row_start_y
        for hero in self.visible_roster():
            row_rect = self.roster_row_rect(y)
            buttons.append(Button((424, row_rect.y + 6, 78, 28), "Add", lambda h=hero: self.add_to_party(h)))
            y += self.ROSTER_ROW_SPACING

        return buttons

    def build_party_buttons(self):
        buttons = []

        y = self.party_row_start_y
        for hero in self.visible_party():
            row_rect = self.party_row_rect(y)
            buttons.append(Button((778, row_rect.y + 6, 76, 28), "Remove", lambda h=hero: self.remove_from_party(h)))
            y += self.PARTY_ROW_SPACING

        return buttons

    def build_detail_buttons(self):
        return [Button((1010, 650, 190, 42), "Start Expedition", self.start_expedition)]

    def handle_row_click(self, pos):
        y = self.dungeon_row_start_y
        for dungeon in self.visible_dungeons():
            if self.dungeon_row_rect(y).collidepoint(pos):
                self.selected_dungeon = dungeon
                self.status_message = f"Selected dungeon: {dungeon.name}"
                return
            y += self.DUNGEON_ROW_SPACING

    def add_to_party(self, hero):
        if hero in self.selected_party:
            return

        if len(self.selected_party) >= self.PARTY_LIMIT:
            self.status_message = "Party is already full."
            return

        self.selected_party.append(hero)

        self.roster_scroll = self.clamp_scroll(self.roster_scroll, len(self.available_roster()), self.ROSTER_VISIBLE_ROWS)
        self.party_scroll = self.clamp_scroll(self.party_scroll, len(self.selected_party), self.PARTY_VISIBLE_ROWS)

        self.status_message = f"Added {hero.name} to party."

    def remove_from_party(self, hero):
        if hero not in self.selected_party:
            return

        self.selected_party.remove(hero)

        self.roster_scroll = self.clamp_scroll(self.roster_scroll, len(self.available_roster()), self.ROSTER_VISIBLE_ROWS)
        self.party_scroll = self.clamp_scroll(self.party_scroll, len(self.selected_party), self.PARTY_VISIBLE_ROWS)

        self.status_message = f"Removed {hero.name} from party."

    def start_expedition(self):
        if not self.selected_party:
            self.status_message = "Choose at least one hero first."
            return

        if self.selected_dungeon is None:
            self.status_message = "Choose a dungeon first."
            return

        self.on_start_expedition(list(self.selected_party), self.selected_dungeon)

    def available_roster(self):
        return [
            hero
            for hero in self.state.roster
            if hero not in self.selected_party and hero.injured_years_remaining <= 0
        ]

    def visible_roster(self):
        available = self.available_roster()
        end = self.roster_scroll + self.ROSTER_VISIBLE_ROWS
        return available[self.roster_scroll:end]

    def visible_party(self):
        end = self.party_scroll + self.PARTY_VISIBLE_ROWS
        return self.selected_party[self.party_scroll:end]

    def visible_dungeons(self):
        end = self.dungeon_scroll + self.DUNGEON_VISIBLE_ROWS
        return self.state.dungeons[self.dungeon_scroll:end]

    def clamp_scroll(self, value, item_count, visible_count):
        max_scroll = max(0, item_count - visible_count)
        return max(0, min(value, max_scroll))

    def draw_scrollbar(self, screen, panel, scroll, item_count, visible_count):
        track_rect = self.scrollbar_track_rect(panel)

        pygame.draw.rect(screen, (44, 44, 54), track_rect, border_radius=4)

        if item_count <= visible_count:
            pygame.draw.rect(screen, (72, 72, 88), track_rect, border_radius=4)
            return

        max_scroll = max(1, item_count - visible_count)
        thumb_height = max(28, int(track_rect.height * (visible_count / item_count)))
        scroll_ratio = scroll / max_scroll
        thumb_y = track_rect.y + int((track_rect.height - thumb_height) * scroll_ratio)

        thumb_rect = pygame.Rect(track_rect.x, thumb_y, track_rect.width, thumb_height)
        pygame.draw.rect(screen, (120, 120, 150), thumb_rect, border_radius=4)

        hint = f"{scroll + 1}-{min(scroll + visible_count, item_count)} of {item_count}"
        screen.blit(self.font.render(hint, True, (160, 160, 175)), (panel.rect.right - 118, panel.rect.bottom - 24))

    def scrollbar_track_rect(self, panel):
        return pygame.Rect(
            panel.rect.right - self.SCROLLBAR_MARGIN - self.SCROLLBAR_WIDTH,
            panel.rect.y + 50,
            self.SCROLLBAR_WIDTH,
            panel.rect.height - 82,
        )

    def truncate_text(self, text, font, max_width):
        if font.size(text)[0] <= max_width:
            return text

        ellipsis = "..."
        trimmed = text

        while trimmed and font.size(trimmed + ellipsis)[0] > max_width:
            trimmed = trimmed[:-1]

        return trimmed + ellipsis

    def roster_row_rect(self, y):
        return pygame.Rect(34, y - 8, 478, 40)

    def party_row_rect(self, y):
        return pygame.Rect(586, y - 8, 276, 40)

    def dungeon_row_rect(self, y):
        return pygame.Rect(930, y - 10, 316, 78)