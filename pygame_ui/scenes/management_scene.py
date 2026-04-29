from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.ui_helpers import truncate_text
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.navigation_buttons import action_button, hub_button
from pygame_ui.widgets.resource_header import ResourceHeader
from pygame_ui.widgets.selection_details_panel import SelectionDetailsPanel
from pygame_ui.widgets.status_chip import StatusChip
from pygame_ui.widgets.text_block import TextBlock
from pygame_ui.widgets.row_styles import draw_selectable_row
from pygame_ui.widgets.scrollable_list_panel import ScrollableListPanel


class ManagementScene(SceneBase):
    def __init__(self, state, on_return_to_hub, on_save_game):
        super().__init__()

        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        self.selected_hero = None
        self.selected_source = ""
        self.status_message = "Guild management active."

        self.details_panel = SelectionDetailsPanel(
            rect=(40, 790, 1840, 230),
            title="Selected Hero Details",
            empty_message="Select a recruit or roster hero to inspect.",
            left_width=560,
            right_width=1160,
        )

        self.recruits_panel = ScrollableListPanel(
            rect=(40, 150, 1080, 600),
            title="Available Recruits",
            row_height=74,
            row_gap=10,
            visible_rows=None,
            font=self.font,
            title_font=self.title_font,
            padding=18,
            title_height=64,
        )

        self.roster_panel = ScrollableListPanel(
            rect=(1160, 150, 720, 600),
            title="Roster",
            row_height=70,
            row_gap=10,
            visible_rows=None,
            font=self.font,
            title_font=self.title_font,
            padding=18,
            title_height=64,
        )

    def roster_capacity(self):
        return self.state.guild_upgrades.roster_capacity

    def sync_lists(self):
        self.recruits_panel.set_items(self.state.available_contracts)
        self.roster_panel.set_items(self.state.roster)

    def handle_event(self, event):
        self.sync_lists()

        if self.recruits_panel.handle_event(event):
            return

        if self.roster_panel.handle_event(event):
            return

        if self.handle_buttons_click(event, self.build_all_buttons()):
            return

        if self.is_left_click(event):
            self.handle_row_click(event.pos)

    def update(self, mouse_pos):
        super().update(mouse_pos)
        self.sync_lists()
        self.recruits_panel.update(mouse_pos)
        self.roster_panel.update(mouse_pos)

    def draw(self, screen):
        self.sync_lists()
        self.clear_screen(screen)

        self.draw_header(screen)

        self.recruits_panel.draw(
            screen=screen,
            row_drawer=self.draw_recruit_row,
            selected_item=self.selected_hero if self.selected_source == "Recruit" else None,
            empty_text="No recruits available.",
        )

        self.roster_panel.draw(
            screen=screen,
            row_drawer=self.draw_roster_row,
            selected_item=self.selected_hero if self.selected_source == "Roster" else None,
            empty_text="No heroes hired yet.",
        )

        self.draw_details(screen)
        self.update_and_draw_buttons(screen, self.build_all_buttons())

    def draw_header(self, screen):
        HeaderPanel(
            rect=(40, 30, 1840, 96),
            title="Guild Management",
            stats="",
            status_message=self.status_message,
            stats_pos=(70, 70),
            status_pos=(1080, 108),
        ).draw(screen, self.title_font, self.header_font, self.font)

        ResourceHeader(
            resources=[
                ("Gold", f"{self.state.gold}g"),
                ("Roster", f"{len(self.state.roster)}/{self.roster_capacity()}"),
                ("Recruits", len(self.state.available_contracts)),
                ("Fallen", len(self.state.fallen_heroes)),
                ("Inventory", len(self.state.inventory)),
            ],
            spacing=185,
        ).draw(screen, self.font, 60, 72)

    def draw_recruit_row(self, screen, hero, row_rect, is_selected, is_hovered):
        can_afford = self.state.gold >= hero.signing_bonus
        roster_full = len(self.state.roster) >= self.roster_capacity()
        can_recruit = can_afford and not roster_full

        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style="dark" if can_recruit else "brown",
        )

        subclass = hero.subclass or "Base"

        screen.blit(
            self.font.render(
                truncate_text(
                    f"{hero.name} | {hero.hero_class}/{subclass} | Lv {hero.level}",
                    self.font,
                    row_rect.width - 250,
                ),
                True,
                theme.TEXT_PRIMARY,
            ),
            (row_rect.x + 14, row_rect.y + 10),
        )

        StatusChip(
            rect=(row_rect.right - 234, row_rect.y + 10, 104, 26),
            text=f"{hero.signing_bonus}g",
            style="good" if can_afford else "danger",
        ).draw(screen, self.small_font)

        StatusChip(
            rect=(row_rect.right - 118, row_rect.y + 10, 104, 26),
            text="Open" if not roster_full else "Full",
            style="good" if not roster_full else "danger",
        ).draw(screen, self.small_font)

        TextBlock(
            lines=[
                (
                    f"Age {hero.age} ({hero.career_stage()}) | "
                    f"Pwr {hero.combat_power()} | Wage {hero.wage_per_year}g | "
                    f"{hero.growth_rate} | {hero.contract_attitude}"
                )
            ],
            color=theme.TEXT_MUTED,
            row_spacing=18,
            max_lines=1,
        ).draw(
            screen=screen,
            font=self.small_font,
            x=row_rect.x + 14,
            y=row_rect.y + 44,
            max_width=row_rect.width - 28,
        )

    def draw_roster_row(self, screen, hero, row_rect, is_selected, is_hovered):
        style = "green"
        if hero.injured_years_remaining > 0:
            style = "brown"

        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style=style,
        )

        subclass = hero.subclass or "Base"

        screen.blit(
            self.font.render(
                truncate_text(
                    f"{hero.name} | {hero.hero_class}/{subclass} | Lv {hero.level}",
                    self.font,
                    row_rect.width - 140,
                ),
                True,
                (210, 240, 210),
            ),
            (row_rect.x + 14, row_rect.y + 10),
        )

        StatusChip(
            rect=(row_rect.right - 118, row_rect.y + 10, 104, 26),
            text=self.satisfaction_label(hero),
            style=self.satisfaction_style(hero),
        ).draw(screen, self.small_font)

        TextBlock(
            lines=[
                (
                    f"Age {hero.age} ({hero.career_stage()}) | "
                    f"Pwr {hero.combat_power()} | Wage {hero.wage_per_year}g | "
                    f"{self.health_text(hero)}"
                )
            ],
            color=(180, 210, 180),
            row_spacing=18,
            max_lines=1,
        ).draw(
            screen=screen,
            font=self.small_font,
            x=row_rect.x + 14,
            y=row_rect.y + 44,
            max_width=row_rect.width - 28,
        )

    def draw_details(self, screen):
        if not self.selected_hero:
            self.details_panel.draw(
                screen=screen,
                title_font=self.title_font,
                font=self.font,
                left_lines=[],
                right_lines=[],
            )
            return

        hero = self.selected_hero

        self.details_panel.details_panel.panel.draw(screen, self.title_font)

        columns = [
            [
                f"Name: {hero.name}",
                f"Source: {self.selected_source}",
                f"Class: {hero.hero_class}",
                f"Subclass: {hero.subclass or 'None'}",
                f"Specialty: {hero.specialty}",
                f"Ability: {hero.special_ability or 'None'}",
            ],
            [
                f"Growth: {hero.growth_rate}",
                f"Attitude: {hero.contract_attitude}",
                f"Satisfaction: {hero.satisfaction}/100",
                f"Contract Years: {hero.contract_years}",
                f"Recruit Cost: {hero.signing_bonus}g",
                f"Dispatch Wage: {hero.wage_per_year}g",
            ],
            [
                f"Power: {hero.combat_power()}",
                f"Age: {hero.age} ({hero.career_stage()})",
                f"Age Power: x{hero.age_power_multiplier():.2f}",
                f"Mentorship: {hero.mentorship_value()}",
                f"Retire Risk: {hero.retirement_chance() * 100:.1f}%",
                f"Health: {self.health_text(hero)}",
            ],
        ]

        start_x = self.details_panel.rect.x + 28
        start_y = self.details_panel.rect.y + 54
        column_width = 590

        for column_index, lines in enumerate(columns):
            x = start_x + column_index * column_width
            y = start_y

            for line in lines:
                screen.blit(
                    self.font.render(line, True, theme.TEXT_SECONDARY),
                    (x, y),
                )
                y += 28

    def build_all_buttons(self):
        buttons = [
            hub_button(self.on_return_to_hub),
        ]

        if self.selected_hero and self.selected_source == "Recruit":
            buttons.append(action_button("Recruit Hero", self.hire_selected_hero, rect=(1440, 956, 180, 44)))

        if self.selected_hero and self.selected_source == "Roster":
            buttons.append(action_button("Release Hero", self.release_selected_hero, rect=(1660, 956, 180, 44)))

        return buttons

    def handle_row_click(self, pos):
        recruit = self.recruits_panel.item_at_pos(pos)
        if recruit is not None:
            self.selected_hero = recruit
            self.selected_source = "Recruit"
            self.status_message = f"Selected recruit: {recruit.name}"
            return

        roster_hero = self.roster_panel.item_at_pos(pos)
        if roster_hero is not None:
            self.selected_hero = roster_hero
            self.selected_source = "Roster"
            self.status_message = f"Selected roster hero: {roster_hero.name}"

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

        self.selected_hero = hero
        self.selected_source = "Roster"
        self.status_message = f"Recruited {hero.name} for {hero.signing_bonus}g."

        self.sync_lists()

        if self.on_save_game:
            self.on_save_game()

    def hire_selected_hero(self):
        if self.selected_hero is not None and self.selected_source == "Recruit":
            self.hire_hero(self.selected_hero)

    def release_hero(self, hero):
        if hero not in self.state.roster:
            return

        self.state.roster.remove(hero)

        if self.selected_hero is hero:
            self.selected_hero = None
            self.selected_source = ""

        self.status_message = f"Released {hero.name} from the guild."
        self.sync_lists()

        if self.on_save_game:
            self.on_save_game()

    def release_selected_hero(self):
        if self.selected_hero is not None and self.selected_source == "Roster":
            self.release_hero(self.selected_hero)

    def satisfaction_label(self, hero):
        if hero.satisfaction >= 75:
            return "Happy"
        if hero.satisfaction >= 45:
            return "Okay"
        return "Unhappy"

    def satisfaction_style(self, hero):
        if hero.satisfaction >= 75:
            return "good"
        if hero.satisfaction >= 45:
            return "warning"
        return "danger"

    def health_text(self, hero):
        if hero.injured_years_remaining > 0:
            return f"Injured {hero.injured_years_remaining}y"
        return hero.health_status()