from game_state import available_dungeons_for_state
from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.ui_helpers import truncate_text
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.key_value_grid import KeyValueGrid
from pygame_ui.widgets.navigation_buttons import action_button, hub_button
from pygame_ui.widgets.party_summary import PartySummary
from pygame_ui.widgets.resource_header import ResourceHeader
from pygame_ui.widgets.selection_details_panel import SelectionDetailsPanel
from pygame_ui.widgets.status_chip import StatusChip
from pygame_ui.widgets.text_block import TextBlock
from pygame_ui.widgets.timeline_strip import TimelineStrip
from pygame_ui.widgets.row_styles import draw_selectable_row
from pygame_ui.widgets.scrollable_list_panel import ScrollableListPanel


class ExpeditionScene(SceneBase):
    def __init__(self, state, on_return_to_hub, on_start_expedition):
        super().__init__()

        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_start_expedition = on_start_expedition

        self.status_message = "Choose a mission, then assign heroes."

        self.selected_party = []
        self.selected_party_hero = None
        self.selected_dungeon = None

        self.details_panel = SelectionDetailsPanel(
            rect=(40, 760, 1840, 260),
            title="Expedition Details",
            empty_message="Choose a mission and assign heroes.",
            left_width=520,
            right_width=520,
        )

        self.roster_panel = ScrollableListPanel(
            rect=(40, 150, 760, 570),
            title="Available Heroes",
            row_height=76,
            row_gap=10,
            visible_rows=None,
            font=self.font,
            title_font=self.title_font,
            padding=18,
            title_height=64,
        )

        self.party_panel = ScrollableListPanel(
            rect=(830, 150, 410, 570),
            title="Party",
            row_height=64,
            row_gap=10,
            visible_rows=None,
            font=self.font,
            title_font=self.title_font,
            padding=18,
            title_height=64,
        )

        self.dungeon_panel = ScrollableListPanel(
            rect=(1270, 150, 610, 570),
            title="Missions",
            row_height=110,
            row_gap=12,
            visible_rows=None,
            font=self.font,
            title_font=self.title_font,
            padding=18,
            title_height=64,
        )

    def sync_lists(self):
        self.roster_panel.set_items(self.available_roster())
        self.party_panel.set_items(self.selected_party)
        self.dungeon_panel.set_items(self.available_dungeons())

        if self.selected_party_hero not in self.selected_party:
            self.selected_party_hero = None

    def available_dungeons(self):
        return available_dungeons_for_state(self.state)

    def party_limit(self):
        if self.selected_dungeon is None:
            return 0
        return self.party_limit_for_dungeon(self.selected_dungeon)

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
            selected_item=self.selected_party_hero,
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
        HeaderPanel(
            rect=(40, 30, 1840, 96),
            title="Expedition Prep",
            stats="",
            status_message=self.status_message,
            stats_pos=(70, 70),
            status_pos=(1080, 108),
        ).draw(screen, self.title_font, self.header_font, self.font)

        party_cap_text = self.party_limit() if self.selected_dungeon else "?"
        ResourceHeader(
            resources=[
                ("Gold", f"{self.state.gold}g"),
                ("Year", self.state.year),
                ("Runs", self.state.expedition - 1),
                ("Party", f"{len(self.selected_party)}/{party_cap_text}"),
            ],
            spacing=210,
            item_max_width=180,
            font_size=24,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=False,
            value_bold=True,
        ).draw(screen, self.font, 60, 72)

    def draw_roster_row(self, screen, hero, row_rect, is_selected, is_hovered):
        ready = hero.injured_years_remaining <= 0
        style = "green" if ready else "brown"

        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=False,
            is_hovered=is_hovered,
            style=style,
        )

        subclass = hero.subclass or "Base"
        button_reserved_width = 46

        screen.blit(
            self.font.render(
                truncate_text(
                    f"{hero.name} | {hero.hero_class}/{subclass} | Lv {hero.level}",
                    self.font,
                    row_rect.width - button_reserved_width - 30,
                ),
                True,
                (210, 240, 210) if ready else theme.TEXT_MUTED,
            ),
            (row_rect.x + 14, row_rect.y + 8),
        )

        if self.selected_dungeon is None:
            chip_text = "Pick Mission"
            chip_style = "locked"
        elif not ready:
            chip_text = "Injured"
            chip_style = "warning"
        elif len(self.selected_party) >= self.party_limit():
            chip_text = "Party Full"
            chip_style = "danger"
        else:
            chip_text = "Ready"
            chip_style = "good"

        StatusChip(
            rect=(row_rect.x + 14, row_rect.y + 42, 110, 24),
            text=chip_text,
            style=chip_style,
        ).draw(screen, self.small_font)

        TextBlock(
            lines=[
                f"Pwr {hero.combat_power()} | Age {hero.age} ({hero.career_stage()}) | Wage {hero.wage_per_year}g | Mentor {hero.mentorship_value()}"
            ],
            color=(180, 210, 180) if ready else theme.TEXT_MUTED,
            row_spacing=18,
            max_lines=1,
        ).draw(
            screen=screen,
            font=self.small_font,
            x=row_rect.x + 136,
            y=row_rect.y + 45,
            max_width=row_rect.width - 190,
        )

    def draw_party_row(self, screen, hero, row_rect, is_selected, is_hovered):
        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style="green",
        )

        button_reserved_width = 46

        screen.blit(
            self.font.render(
                truncate_text(
                    f"{hero.name} | Lv {hero.level}",
                    self.font,
                    row_rect.width - button_reserved_width - 24,
                ),
                True,
                (210, 240, 210),
            ),
            (row_rect.x + 12, row_rect.y + 8),
        )

        TextBlock(
            lines=[f"{hero.hero_class} | {hero.career_stage()} | Wage {hero.wage_per_year}g | Pwr {hero.combat_power()}"],
            color=(180, 210, 180),
            row_spacing=18,
            max_lines=1,
        ).draw(
            screen=screen,
            font=self.small_font,
            x=row_rect.x + 12,
            y=row_rect.y + 38,
            max_width=row_rect.width - button_reserved_width - 18,
        )

    def draw_dungeon_row(self, screen, dungeon, row_rect, is_selected, is_hovered):
        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style="brown",
        )

        mission_party_limit = self.party_limit_for_dungeon(dungeon)

        screen.blit(
            self.font.render(
                truncate_text(dungeon.name, self.font, row_rect.width - 24),
                True,
                (240, 230, 210),
            ),
            (row_rect.x + 14, row_rect.y + 8),
        )

        StatusChip(
            rect=(row_rect.x + 14, row_rect.y + 40, 78, 24),
            text=f"Diff {dungeon.difficulty}",
            style="warning" if dungeon.difficulty >= 3 else "info",
        ).draw(screen, self.small_font)

        StatusChip(
            rect=(row_rect.x + 102, row_rect.y + 40, 92, 24),
            text=f"Party {mission_party_limit}",
            style="default",
        ).draw(screen, self.small_font)

        enemy_chip_width = min(120, max(84, 24 + len(dungeon.enemy_type) * 8))
        StatusChip(
            rect=(row_rect.x + 204, row_rect.y + 40, enemy_chip_width, 24),
            text=dungeon.enemy_type,
            style="default",
        ).draw(screen, self.small_font)

        TextBlock(
            lines=[f"Loot {dungeon.loot_min}-{dungeon.loot_max}g | Enemy {dungeon.enemy_power} | Rooms {dungeon.room_count}"],
            color=(205, 195, 180),
            row_spacing=18,
            max_lines=1,
        ).draw(
            screen=screen,
            font=self.small_font,
            x=row_rect.x + 14,
            y=row_rect.y + 76,
            max_width=row_rect.width - 28,
        )

    def draw_details(self, screen):
        self.details_panel.details_panel.panel.draw(screen, self.title_font)

        panel = self.details_panel.rect
        col1_x = panel.x + 28
        col2_x = panel.x + 610
        col3_x = panel.x + 1190
        start_y = panel.y + 52

        party_summary = PartySummary(self.selected_party)
        party_summary.draw(screen, self.small_font, col1_x, start_y)

        left_grid_y = start_y + 92
        KeyValueGrid(
            rows=[
                ("Dispatch Cost", f"{self.total_expedition_cost()}g"),
                ("Selected Heroes", ", ".join(hero.name for hero in self.selected_party) or "None"),
                ("Focused Hero", self.selected_party_hero.name if self.selected_party_hero is not None else "None"),
            ],
            columns=1,
            column_width=500,
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
            x=col1_x,
            y=left_grid_y,
        )

        if self.selected_dungeon is None:
            KeyValueGrid(
                rows=[
                    ("Mission", "None selected"),
                    ("Guidance", "Pick a mission to set party size and risk level."),
                ],
                columns=1,
                column_width=500,
                row_gap=10,
                label_color=theme.TEXT_MUTED,
                value_color=theme.TEXT_PRIMARY,
                label_bold=True,
                value_bold=False,
                font_size=22,
                line_spacing=2,
            ).draw(screen, self.font, col2_x, start_y)

            KeyValueGrid(
                rows=[
                    ("Party Status", "Not Ready"),
                    ("Assigned", "0 hero(es)"),
                ],
                columns=1,
                column_width=360,
                row_gap=10,
                label_color=theme.TEXT_MUTED,
                value_color=theme.TEXT_MUTED,
                label_bold=True,
                value_bold=False,
                font_size=22,
                line_spacing=2,
            ).draw(screen, self.font, col3_x, start_y + 32)
            return

        dungeon = self.selected_dungeon

        TimelineStrip(
            rect=(col2_x, start_y + 2, 420, 18),
            total_steps=max(1, self.party_limit()),
            current_step=min(len(self.selected_party), max(0, self.party_limit() - 1)),
        ).draw(screen)

        KeyValueGrid(
            rows=[
                ("Mission", dungeon.name),
                ("Enemy Type", dungeon.enemy_type),
                ("Enemy Power", dungeon.enemy_power),
                ("Difficulty", dungeon.difficulty),
                ("Party Limit", self.party_limit()),
            ],
            columns=1,
            column_width=500,
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
            x=col2_x,
            y=start_y + 32,
        )

        KeyValueGrid(
            rows=[
                ("Loot", f"{dungeon.loot_min}-{dungeon.loot_max}g"),
                ("Party Status", "Ready" if self.can_start_expedition() else "Not Ready"),
                ("Assigned", f"{len(self.selected_party)} hero(es)"),
                ("Focused", self.selected_party_hero.name if self.selected_party_hero is not None else "None"),
            ],
            columns=1,
            column_width=360,
            row_gap=10,
            label_color=theme.TEXT_MUTED,
            value_color=(190, 220, 190) if self.can_start_expedition() else theme.TEXT_MUTED,
            label_bold=True,
            value_bold=False,
            font_size=22,
            line_spacing=2,
        ).draw(
            screen=screen,
            font=self.font,
            x=col3_x,
            y=start_y + 32,
        )

    def build_all_buttons(self):
        buttons = [hub_button(self.on_return_to_hub)]

        buttons.extend(self.build_roster_buttons())
        buttons.extend(self.build_party_buttons())

        footer_y = self.details_panel.rect.bottom - 54

        label = "Start Expedition" if self.can_start_expedition() else "Cannot Start"
        buttons.append(
            action_button(
                label,
                self.start_expedition,
                rect=(self.details_panel.rect.right - 220, footer_y, 190, 42),
            )
        )

        return buttons

    def build_roster_buttons(self):
        buttons = []

        y = self.roster_panel.row_start_y()
        for hero in self.roster_panel.visible_items():
            row_rect = self.roster_panel.row_rect(y)
            buttons.append(
                action_button(
                    "+",
                    lambda h=hero: self.add_to_party(h),
                    rect=(row_rect.right - 36, row_rect.y + 24, 24, 24),
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
                action_button(
                    "-",
                    lambda h=hero: self.remove_from_party(h),
                    rect=(row_rect.right - 36, row_rect.y + 20, 24, 24),
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
            return

        party_hero = self.party_panel.item_at_pos(pos)
        if party_hero is not None:
            self.selected_party_hero = party_hero
            self.status_message = f"Selected party hero: {party_hero.name}"

    def add_to_party(self, hero):
        if hero in self.selected_party:
            return

        if self.selected_dungeon is None:
            self.status_message = "Choose a mission first so party limit is known."
            return

        if hero.injured_years_remaining > 0:
            self.status_message = f"{hero.name} is injured and cannot be deployed."
            return

        if len(self.selected_party) >= self.party_limit():
            self.status_message = f"This mission allows {self.party_limit()} hero(es)."
            return

        self.selected_party.append(hero)
        self.selected_party_hero = hero
        self.sync_lists()
        self.status_message = f"Added {hero.name} to party."

    def remove_from_party(self, hero):
        if hero not in self.selected_party:
            return

        self.selected_party.remove(hero)

        if self.selected_party_hero is hero:
            self.selected_party_hero = None

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

    def can_start_expedition(self):
        if self.selected_dungeon is None:
            return False
        if not self.selected_party:
            return False
        if len(self.selected_party) > self.party_limit():
            return False
        if self.state.gold < self.total_expedition_cost():
            return False
        return True

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