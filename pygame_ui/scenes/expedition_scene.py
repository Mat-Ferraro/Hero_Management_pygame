from game_state import available_dungeons_for_state
from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.ui_helpers import truncate_text
from pygame_ui.widgets.details_panel import DetailsPanel
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.row_styles import draw_selectable_row
from pygame_ui.widgets.scrollable_list_panel import ScrollableListPanel

from ..widgets.button import Button


class ExpeditionScene(SceneBase):
    def __init__(self, state, on_return_to_hub, on_start_expedition):
        super().__init__()

        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_start_expedition = on_start_expedition

        self.status_message = "Choose a mission, then assign heroes."

        self.selected_party = []
        self.selected_dungeon = None

        self.details_panel = DetailsPanel((20, 548, 1240, 160), "Expedition Details")

        self.roster_panel = ScrollableListPanel(
            rect=(20, 120, 520, 410),
            title="Available Heroes",
            row_height=40,
            row_spacing=48,
            visible_rows=6,
            font=self.font,
            title_font=self.title_font,
            padding=14,
            title_height=60,
        )

        self.party_panel = ScrollableListPanel(
            rect=(560, 120, 320, 410),
            title="Party",
            row_height=40,
            row_spacing=48,
            visible_rows=4,
            font=self.font,
            title_font=self.title_font,
            padding=26,
            title_height=60,
        )

        self.dungeon_panel = ScrollableListPanel(
            rect=(900, 120, 360, 410),
            title="Missions",
            row_height=78,
            row_spacing=84,
            visible_rows=4,
            font=self.font,
            title_font=self.title_font,
            padding=30,
            title_height=60,
        )

    def sync_lists(self):
        self.roster_panel.set_items(self.available_roster())
        self.party_panel.set_items(self.selected_party)
        self.dungeon_panel.set_items(self.available_dungeons())

    def party_limit(self):
        if self.selected_dungeon is None:
            return 0
        return self.party_limit_for_dungeon(self.selected_dungeon)

    def available_dungeons(self):
        return available_dungeons_for_state(self.state)

    def handle_event(self, event):
        self.sync_lists()

        if self.roster_panel.handle_event(event):
            return

        if self.party_panel.handle_event(event):
            return

        if self.dungeon_panel.handle_event(event):
            return

        if self.handle_buttons_click(event, self.build_all_buttons()):
            return

        if self.is_left_click(event):
            self.handle_row_click(event.pos)

    def update(self, mouse_pos):
        super().update(mouse_pos)
        self.sync_lists()
        self.roster_panel.update(mouse_pos)
        self.party_panel.update(mouse_pos)
        self.dungeon_panel.update(mouse_pos)

    def draw(self, screen):
        self.sync_lists()
        self.clear_screen(screen)

        self.draw_header(screen)

        self.roster_panel.draw(
            screen=screen,
            row_drawer=self.draw_roster_row,
            selected_item=None,
            empty_text="No available heroes.",
        )

        self.party_panel.draw(
            screen=screen,
            row_drawer=self.draw_party_row,
            selected_item=None,
            empty_text="No party selected.",
        )

        self.dungeon_panel.draw(
            screen=screen,
            row_drawer=self.draw_dungeon_row,
            selected_item=self.selected_dungeon,
            empty_text="No missions unlocked.",
        )

        self.draw_details(screen)
        self.update_and_draw_buttons(screen, self.build_all_buttons())

    def draw_header(self, screen):
        party_cap_text = self.party_limit() if self.selected_dungeon else "?"

        stats = (
            f"Gold: {self.state.gold}g    "
            f"Campaign Year: {self.state.year}    "
            f"Campaigns: {self.state.expedition - 1}    "
            f"Party: {len(self.selected_party)}/{party_cap_text}"
        )

        HeaderPanel(
            title="Expedition Prep",
            stats=stats,
            status_message=self.status_message,
        ).draw(screen, self.title_font, self.header_font, self.font)

    def draw_roster_row(self, screen, hero, row_rect, is_selected, is_hovered):
        draw_selectable_row(screen, row_rect, False, is_hovered, style="dark")

        subclass = hero.subclass or "Base"
        line = (
            f"{hero.name} | {hero.hero_class}/{subclass} | "
            f"Lv {hero.level} | {hero.career_stage()} | Pwr {hero.combat_power()}"
        )

        rendered_line = truncate_text(line, self.font, row_rect.width - 100)
        screen.blit(self.font.render(rendered_line, True, theme.TEXT_PRIMARY), (row_rect.x + 12, row_rect.y + 11))

    def draw_party_row(self, screen, hero, row_rect, is_selected, is_hovered):
        draw_selectable_row(screen, row_rect, False, is_hovered, style="green")

        line = f"{hero.name} | {hero.career_stage()}"
        rendered_line = truncate_text(line, self.font, row_rect.width - 100)

        screen.blit(self.font.render(rendered_line, True, (210, 240, 210)), (row_rect.x + 12, row_rect.y + 11))

    def draw_dungeon_row(self, screen, dungeon, row_rect, is_selected, is_hovered):
        draw_selectable_row(screen, row_rect, is_selected, is_hovered, style="brown")

        mission_party_limit = self.party_limit_for_dungeon(dungeon)

        line_1 = truncate_text(dungeon.name, self.font, row_rect.width - 24)
        line_2 = f"Diff {dungeon.difficulty} | Party {mission_party_limit} | {dungeon.room_count} rooms"
        line_3 = f"Loot {dungeon.loot_min}-{dungeon.loot_max}g"

        screen.blit(self.font.render(line_1, True, (240, 230, 210)), (row_rect.x + 12, row_rect.y + 10))
        screen.blit(self.font.render(line_2, True, (205, 195, 180)), (row_rect.x + 12, row_rect.y + 34))
        screen.blit(self.font.render(line_3, True, (190, 180, 165)), (row_rect.x + 12, row_rect.y + 58))

    def draw_details(self, screen):
        party_power = sum(hero.combat_power() for hero in self.selected_party)
        expedition_cost = self.total_expedition_cost()

        lines = [
            f"Party Power: {party_power}",
            f"Dispatch Cost: {expedition_cost}g",
            f"Selected Heroes: {', '.join(hero.name for hero in self.selected_party) or 'None'}",
        ]

        if self.selected_party:
            mentorship_total = sum(hero.mentorship_value() for hero in self.selected_party)
            lines.append(f"Party Mentorship Value: {mentorship_total}")

        if self.selected_dungeon:
            dungeon = self.selected_dungeon
            lines.extend(
                [
                    f"Mission: {dungeon.name}",
                    (
                        f"Enemy: {dungeon.enemy_type}    "
                        f"Enemy Power: {dungeon.enemy_power}    "
                        f"Difficulty: {dungeon.difficulty}    "
                        f"Party Limit: {self.party_limit()}"
                    ),
                ]
            )
        else:
            lines.append("Mission: None selected")

        self.details_panel.draw_lines(
            screen=screen,
            title_font=self.title_font,
            font=self.font,
            lines=lines[:5],
            max_width=1100,
        )

    def build_all_buttons(self):
        buttons = [Button(theme.HUB_BUTTON_RECT, "Hub", self.on_return_to_hub)]

        buttons.extend(self.build_roster_buttons())
        buttons.extend(self.build_party_buttons())
        buttons.append(Button((1010, 650, 190, 42), "Start Expedition", self.start_expedition))

        return buttons

    def build_roster_buttons(self):
        buttons = []

        y = self.roster_panel.row_start_y()
        for hero in self.roster_panel.visible_items():
            row_rect = self.roster_panel.row_rect(y)
            buttons.append(
                Button(
                    (row_rect.right - 88, row_rect.y + 6, 78, 28),
                    "Add",
                    lambda h=hero: self.add_to_party(h),
                )
            )
            y += self.roster_panel.row_spacing

        return buttons

    def build_party_buttons(self):
        buttons = []

        y = self.party_panel.row_start_y()
        for hero in self.party_panel.visible_items():
            row_rect = self.party_panel.row_rect(y)
            buttons.append(
                Button(
                    (row_rect.right - 86, row_rect.y + 6, 76, 28),
                    "Remove",
                    lambda h=hero: self.remove_from_party(h),
                )
            )
            y += self.party_panel.row_spacing

        return buttons

    def handle_row_click(self, pos):
        dungeon = self.dungeon_panel.item_at_pos(pos)
        if dungeon is not None:
            self.selected_dungeon = dungeon
            self.trim_party_to_limit()
            self.status_message = f"Selected mission: {dungeon.name}"

    def add_to_party(self, hero):
        if hero in self.selected_party:
            return

        if self.selected_dungeon is None:
            self.status_message = "Choose a mission first so party limit is known."
            return

        if len(self.selected_party) >= self.party_limit():
            self.status_message = f"This mission allows {self.party_limit()} hero(es)."
            return

        self.selected_party.append(hero)
        self.sync_lists()
        self.status_message = f"Added {hero.name} to party."

    def remove_from_party(self, hero):
        if hero not in self.selected_party:
            return

        self.selected_party.remove(hero)
        self.sync_lists()
        self.status_message = f"Removed {hero.name} from party."

    def start_expedition(self):
        if self.selected_dungeon is None:
            self.status_message = "Choose a mission first."
            return

        if not self.selected_party:
            self.status_message = "Choose at least one hero first."
            return

        if len(self.selected_party) > self.party_limit():
            self.status_message = f"This mission allows only {self.party_limit()} hero(es)."
            return

        expedition_cost = self.total_expedition_cost()
        if self.state.gold < expedition_cost:
            self.status_message = f"Not enough gold. Expedition costs {expedition_cost}g."
            return

        self.state.gold -= expedition_cost
        self.status_message = f"Paid {expedition_cost}g to dispatch party."

        self.on_start_expedition(list(self.selected_party), self.selected_dungeon)

    def total_expedition_cost(self):
        return sum(hero.wage_per_year for hero in self.selected_party)

    def available_roster(self):
        return [
            hero
            for hero in self.state.roster
            if hero not in self.selected_party and hero.injured_years_remaining <= 0
        ]

    def party_limit_for_dungeon(self, dungeon):
        difficulty = dungeon.difficulty

        if difficulty <= 1:
            return 1

        if difficulty == 2:
            return 2

        if difficulty == 3:
            return 3

        return 4

    def trim_party_to_limit(self):
        limit = self.party_limit()
        if limit <= 0:
            return

        if len(self.selected_party) > limit:
            self.selected_party = self.selected_party[:limit]
            self.sync_lists()
            self.status_message = f"Party trimmed to mission limit of {limit}."