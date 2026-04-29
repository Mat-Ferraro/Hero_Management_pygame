import pygame

from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.ui_helpers import truncate_text
from pygame_ui.widgets.details_panel import DetailsPanel
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.row_styles import draw_selectable_row
from pygame_ui.widgets.scrollable_list_panel import ScrollableListPanel
from pygame_ui.widgets.scrollable_text_panel import ScrollableTextPanel
from systems.training_system import can_train_hero, train_hero, training_cost, training_xp

from ..widgets.button import Button


class TrainingScene(SceneBase):
    def __init__(self, state, on_return_to_hub, on_save_game):
        super().__init__()

        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        self.status_message = "Select a hero to train."
        self.selected_hero = None
        self.stat_font = pygame.font.SysFont(None, 26)

        self.details_panel = DetailsPanel((760, 120, 500, 260), "Training Details")
        self.footer_panel = DetailsPanel((20, 570, 1240, 135), "Career Notes")

        self.heroes_panel = ScrollableListPanel(
            rect=(20, 120, 720, 430),
            title="Roster",
            row_height=50,
            row_spacing=58,
            visible_rows=6,
            font=self.font,
            title_font=self.title_font,
            padding=14,
            title_height=60,
        )

        self.log_panel = ScrollableTextPanel(
            rect=(760, 400, 500, 150),
            title="Training Log",
            font=self.small_font,
            title_font=self.title_font,
            row_spacing=22,
            padding=24,
            title_height=50,
        )
        self.log_panel.set_lines(["Training Hall opened."])

    def sync_lists(self):
        self.heroes_panel.set_items(self.state.roster)

    def handle_event(self, event):
        self.sync_lists()

        if self.heroes_panel.handle_event(event):
            return

        if self.log_panel.handle_event(event):
            return

        if self.handle_buttons_click(event, self.build_buttons()):
            return

        if self.is_left_click(event):
            self.handle_row_click(event.pos)

    def update(self, mouse_pos):
        super().update(mouse_pos)
        self.sync_lists()
        self.heroes_panel.update(mouse_pos)
        self.log_panel.update(mouse_pos)

    def draw(self, screen):
        self.sync_lists()
        self.clear_screen(screen)

        self.draw_header(screen)

        self.heroes_panel.draw(
            screen=screen,
            row_drawer=self.draw_hero_row,
            selected_item=self.selected_hero,
            empty_text="No heroes available.",
        )

        self.draw_details(screen)
        self.log_panel.draw(screen)
        self.draw_footer(screen)

        self.update_and_draw_buttons(screen, self.build_buttons())

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

        HeaderPanel(
            title="Training Hall",
            stats=stats,
            status_message=self.status_message,
        ).draw(screen, self.title_font, self.header_font, self.font)

    def draw_hero_row(self, screen, hero, row_rect, is_selected, is_hovered):
        draw_selectable_row(screen, row_rect, is_selected, is_hovered, style="green")

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
            self.font.render(truncate_text(line_1, self.font, row_rect.width - 24), True, (210, 240, 210)),
            (row_rect.x + 12, row_rect.y + 8),
        )
        screen.blit(
            self.small_font.render(truncate_text(line_2, self.small_font, row_rect.width - 24), True, (180, 210, 180)),
            (row_rect.x + 12, row_rect.y + 32),
        )

    def draw_details(self, screen):
        level = self.state.guild_upgrades.training_hall_level
        cost = training_cost(level)
        xp = training_xp(level)

        self.details_panel.panel.draw(screen, self.title_font)
        self.draw_training_price_badge(screen, self.details_panel.rect, cost, xp)

        text_x = self.details_panel.rect.x + 30
        y = self.details_panel.rect.y + 60
        text_width = self.details_panel.rect.width - 200

        if self.selected_hero is None:
            lines = ["Select a hero to inspect training results."]
        else:
            hero = self.selected_hero
            allowed, reason = can_train_hero(hero)

            lines = [
                f"Hero: {hero.name}",
                f"Class: {hero.hero_class}    Subclass: {hero.subclass or 'None'}",
                f"Ability: {hero.special_ability or 'None'}",
                f"Level: {hero.level}    XP: {hero.xp}/{hero.xp_to_next_level()}",
                f"Status: {'Ready' if allowed else reason}",
            ]

        from pygame_ui.ui_helpers import wrap_text

        for line in lines:
            for wrapped in wrap_text(line, self.small_font, text_width):
                screen.blit(self.small_font.render(wrapped, True, theme.TEXT_SECONDARY), (text_x, y))
                y += 20

    def draw_training_price_badge(self, screen, panel_rect, cost, xp):
        badge_rect = pygame.Rect(panel_rect.right - 160, panel_rect.y + 50, 130, 70)

        pygame.draw.rect(screen, (48, 48, 62), badge_rect, border_radius=8)
        pygame.draw.rect(screen, (150, 150, 190), badge_rect, 2, border_radius=8)

        screen.blit(self.small_font.render("Cost", True, theme.TEXT_MUTED), (badge_rect.x + 14, badge_rect.y + 8))
        screen.blit(self.stat_font.render(f"{cost}g", True, (245, 235, 210)), (badge_rect.x + 14, badge_rect.y + 26))
        screen.blit(self.small_font.render(f"+{xp} XP", True, (190, 220, 190)), (badge_rect.x + 14, badge_rect.y + 48))

    def draw_footer(self, screen):
        lines = [
            "Training is safe but costs gold. Expeditions remain the fastest way to grow heroes.",
            "Future Training Hall upgrades will unlock subclass choices and special abilities.",
            "Older heroes may lose raw power, but their mentorship and learned abilities can remain valuable.",
        ]

        self.footer_panel.draw_lines(
            screen=screen,
            title_font=self.title_font,
            font=self.small_font,
            lines=lines,
            max_width=1120,
        )

    def build_buttons(self):
        buttons = [Button(theme.HUB_BUTTON_RECT, "Hub", self.on_return_to_hub)]

        if self.selected_hero is not None:
            buttons.append(Button((1010, 318, 190, 42), "Train Hero", self.train_selected_hero))

        return buttons

    def handle_row_click(self, pos):
        hero = self.heroes_panel.item_at_pos(pos)
        if hero is not None:
            self.selected_hero = hero
            self.status_message = f"Selected hero: {hero.name}"

    def train_selected_hero(self):
        if self.selected_hero is None:
            self.status_message = "Select a hero first."
            return

        messages = train_hero(self.state, self.selected_hero)
        self.log_panel.append_lines(messages, auto_scroll=True)
        self.status_message = messages[-1] if messages else "Training complete."

        if self.on_save_game:
            self.on_save_game()