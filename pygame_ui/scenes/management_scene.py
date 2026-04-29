from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.ui_helpers import truncate_text
from pygame_ui.widgets.details_panel import DetailsPanel
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.row_styles import draw_selectable_row
from pygame_ui.widgets.scrollable_list_panel import ScrollableListPanel

from ..widgets.button import Button


class ManagementScene(SceneBase):
    def __init__(self, state, on_return_to_hub, on_save_game):
        super().__init__()

        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        self.selected_hero = None
        self.selected_source = ""
        self.status_message = "Guild management active."

        self.details_panel = DetailsPanel((20, 500, 1240, 190), "Selected Hero Details")

        self.recruits_panel = ScrollableListPanel(
            rect=(20, 120, 740, 360),
            title="Available Recruits",
            row_height=58,
            row_spacing=66,
            visible_rows=4,
            font=self.font,
            title_font=self.title_font,
            padding=14,
            title_height=60,
        )

        self.roster_panel = ScrollableListPanel(
            rect=(780, 120, 480, 360),
            title="Roster",
            row_height=50,
            row_spacing=58,
            visible_rows=4,
            font=self.font,
            title_font=self.title_font,
            padding=14,
            title_height=60,
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
        stats = (
            f"Gold: {self.state.gold}g    "
            f"Campaign Year: {self.state.year}    "
            f"Roster: {len(self.state.roster)}/{self.roster_capacity()}    "
            f"Available Recruits: {len(self.state.available_contracts)}"
        )

        HeaderPanel(
            title="Guild Management",
            stats=stats,
            status_message=self.status_message,
        ).draw(screen, self.title_font, self.header_font, self.font)

    def draw_recruit_row(self, screen, hero, row_rect, is_selected, is_hovered):
        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style="dark",
        )

        subclass = hero.subclass or "No Subclass"

        line_1 = (
            f"{hero.name} | {hero.hero_class} | {subclass} | "
            f"Lv {hero.level} | Age {hero.age} ({hero.career_stage()})"
        )
        line_2 = (
            f"Pwr {hero.combat_power()} | Age x{hero.age_power_multiplier():.2f} | "
            f"Recruit {hero.signing_bonus}g | Dispatch {hero.wage_per_year}g"
        )

        screen.blit(
            self.font.render(truncate_text(line_1, self.font, row_rect.width - 24), True, theme.TEXT_PRIMARY),
            (row_rect.x + 12, row_rect.y + 8),
        )
        screen.blit(
            self.small_font.render(truncate_text(line_2, self.small_font, row_rect.width - 24), True, theme.TEXT_MUTED),
            (row_rect.x + 12, row_rect.y + 34),
        )

    def draw_roster_row(self, screen, hero, row_rect, is_selected, is_hovered):
        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style="green",
        )

        subclass = hero.subclass or "No Subclass"
        line_1 = f"{hero.name} | {hero.hero_class} | {subclass} | Lv {hero.level}"
        line_2 = (
            f"Age {hero.age} ({hero.career_stage()}) | "
            f"Pwr {hero.combat_power()} | Sat {hero.satisfaction}/100"
        )

        screen.blit(
            self.font.render(truncate_text(line_1, self.font, row_rect.width - 24), True, (210, 240, 210)),
            (row_rect.x + 12, row_rect.y + 8),
        )
        screen.blit(
            self.small_font.render(truncate_text(line_2, self.small_font, row_rect.width - 24), True, (180, 210, 180)),
            (row_rect.x + 12, row_rect.y + 32),
        )

    def draw_details(self, screen):
        if not self.selected_hero:
            self.details_panel.draw_empty(
                screen=screen,
                title_font=self.title_font,
                font=self.font,
                message="Select a recruit or roster hero to inspect.",
            )
            return

        hero = self.selected_hero

        left_lines = [
            f"Name: {hero.name}",
            f"Class: {hero.hero_class}    Subclass: {hero.subclass or 'None'}",
            f"Special Ability: {hero.special_ability or 'None'}",
            f"Age: {hero.age}    Stage: {hero.career_stage()}    Retires Around: {hero.retirement_age()}",
            f"Satisfaction: {hero.satisfaction}/100 ({hero.satisfaction_label()})",
            f"Recruit Cost: {hero.signing_bonus}g    Dispatch Cost: {hero.wage_per_year}g",
        ]

        right_lines = [
            f"Power: {hero.combat_power()}    Age Power: x{hero.age_power_multiplier():.2f}",
            f"Mentorship Value: {hero.mentorship_value()}",
            f"Retirement Risk: {hero.retirement_chance() * 100:.1f}%",
            f"Stats: Might {hero.total_stat('might')} | Agility {hero.total_stat('agility')} | Mind {hero.total_stat('mind')} | Spirit {hero.total_stat('spirit')}",
            f"Specialty: {hero.specialty}",
            f"XP: {hero.xp}/{hero.xp_to_next_level()}",
            f"Injury: {hero.injured_years_remaining} year(s)" if hero.injured_years_remaining else "Injury: None",
        ]

        self.details_panel.draw_two_columns(
            screen=screen,
            title_font=self.title_font,
            font=self.small_font,
            left_lines=left_lines,
            right_lines=right_lines,
            left_width=540,
            right_width=540,
        )

    def build_all_buttons(self):
        buttons = [
            Button(theme.HUB_BUTTON_RECT, "Hub", self.on_return_to_hub),
        ]

        if self.selected_hero and self.selected_source == "Recruit":
            buttons.append(Button(theme.DETAIL_ACTION_BUTTON_RECT, "Recruit Hero", self.hire_selected_hero))

        if self.selected_hero and self.selected_source == "Roster":
            buttons.append(Button(theme.DETAIL_ACTION_BUTTON_RECT, "Release Hero", self.release_selected_hero))

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