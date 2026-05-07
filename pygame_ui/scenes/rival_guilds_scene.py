from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.ui_helpers import truncate_text
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.key_value_grid import KeyValueGrid
from pygame_ui.widgets.panel import Panel
from pygame_ui.widgets.row_styles import draw_selectable_row
from pygame_ui.widgets.scrollable_list_panel import ScrollableListPanel
from pygame_ui.widgets.status_chip import StatusChip
from pygame_ui.widgets.text_block import TextBlock
from systems.guild.rival_guilds import ensure_rival_guild_state, guild_power, recent_market_history

from ..widgets.button import Button


class RivalGuildsScene(SceneBase):
    def __init__(self, state, on_return_to_hub, on_save_game):
        super().__init__()

        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        ensure_rival_guild_state(self.state)

        self.selected_guild = None
        if self.state.rival_guilds:
            self.selected_guild = self.state.rival_guilds[0]

        self.status_message = "Inspect rival guild rosters."

        self.guilds_panel = ScrollableListPanel(
            rect=(40, 150, 560, 860),
            title="Rival Guilds",
            row_height=74,
            row_gap=10,
            visible_rows=None,
            font=self.font,
            title_font=self.title_font,
            padding=18,
            title_height=64,
        )

        self.details_panel = Panel((630, 150, 1250, 190), "Guild Details")
        self.roster_panel = ScrollableListPanel(
            rect=(630, 360, 780, 650),
            title="Rival Roster",
            row_height=64,
            row_gap=10,
            visible_rows=None,
            font=self.font,
            title_font=self.title_font,
            padding=18,
            title_height=64,
        )
        self.history_panel = Panel((1430, 360, 450, 650), "Recent Market History")

    def sync_lists(self):
        ensure_rival_guild_state(self.state)
        self.guilds_panel.set_items(self.state.rival_guilds)

        if self.selected_guild is None and self.state.rival_guilds:
            self.selected_guild = self.state.rival_guilds[0]

        if self.selected_guild not in self.state.rival_guilds and self.state.rival_guilds:
            self.selected_guild = self.state.rival_guilds[0]

        roster = self.selected_guild["roster"] if self.selected_guild else []
        self.roster_panel.set_items(roster)

    def handle_event(self, event):
        self.sync_lists()

        if self.guilds_panel.handle_event(event):
            return

        if self.roster_panel.handle_event(event):
            return

        if self.handle_buttons_click(event, self.build_buttons()):
            return

        if self.is_left_click(event):
            self.handle_row_click(event.pos)

    def update(self, mouse_pos):
        super().update(mouse_pos)
        self.sync_lists()
        self.guilds_panel.update(mouse_pos)
        self.roster_panel.update(mouse_pos)

    def draw(self, screen):
        self.sync_lists()
        self.clear_screen(screen)

        self.draw_header(screen)

        self.guilds_panel.draw(
            screen=screen,
            row_drawer=self.draw_guild_row,
            selected_item=self.selected_guild,
            empty_text="No rival guilds found.",
        )

        self.details_panel.draw(screen, self.title_font)

        self.roster_panel.draw(
            screen=screen,
            row_drawer=self.draw_roster_row,
            selected_item=None,
            empty_text="This rival guild has no recorded heroes yet.",
        )

        self.history_panel.draw(screen, self.title_font)

        self.draw_details(screen)
        self.draw_history(screen)
        self.update_and_draw_buttons(screen, self.build_buttons())

    def draw_header(self, screen):
        ensure_rival_guild_state(self.state)

        total_rival_heroes = sum(len(guild.get("roster", [])) for guild in self.state.rival_guilds)

        stats = (
            f"Rival Guilds: {len(self.state.rival_guilds)}    "
            f"Tracked Rival Heroes: {total_rival_heroes}    "
            f"Campaign Year: {self.state.year}"
        )

        HeaderPanel(
            rect=(40, 30, 1840, 96),
            title="Rival Guilds",
            stats=stats,
            status_message=self.status_message,
            stats_pos=(70, 74),
            status_pos=(1140, 112),
        ).draw(screen, self.title_font, self.header_font, self.font)

    def draw_guild_row(self, screen, guild, row_rect, is_selected, is_hovered):
        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style="dark",
        )

        screen.blit(
            self.font.render(
                truncate_text(guild["name"], self.font, row_rect.width - 180),
                True,
                theme.TEXT_PRIMARY,
            ),
            (row_rect.x + 14, row_rect.y + 10),
        )

        style_text = f"{guild['style']} | Power {guild_power(guild)} | Heroes {len(guild['roster'])}"
        screen.blit(
            self.small_font.render(
                truncate_text(style_text, self.small_font, row_rect.width - 28),
                True,
                theme.TEXT_SECONDARY,
            ),
            (row_rect.x + 14, row_rect.y + 42),
        )

    def draw_roster_row(self, screen, hero, row_rect, is_selected, is_hovered):
        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=False,
            is_hovered=is_hovered,
            style="dark",
        )

        subclass = hero.subclass or "Base"
        top_line = f"{hero.name} | {hero.hero_class}/{subclass} | Lv {hero.level} | Age {hero.age}"
        bottom_line = (
            f"Pwr {hero.combat_power()} | Growth {hero.growth_rate} | "
            f"Specialty {hero.specialty}"
        )

        screen.blit(
            self.font.render(
                truncate_text(top_line, self.font, row_rect.width - 110),
                True,
                theme.TEXT_PRIMARY,
            ),
            (row_rect.x + 14, row_rect.y + 10),
        )
        screen.blit(
            self.small_font.render(
                truncate_text(bottom_line, self.small_font, row_rect.width - 110),
                True,
                theme.TEXT_SECONDARY,
            ),
            (row_rect.x + 14, row_rect.y + 40),
        )

        StatusChip(
            rect=(row_rect.right - 96, row_rect.y + 18, 78, 24),
            text=f"{hero.contract_years}c",
            style="info",
        ).draw(screen, self.small_font)

    def draw_details(self, screen):
        if self.selected_guild is None:
            return

        guild = self.selected_guild
        left_x = self.details_panel.rect.x + 24
        middle_x = self.details_panel.rect.x + 420
        right_x = self.details_panel.rect.x + 860
        top_y = self.details_panel.rect.y + 52

        recent = guild.get("recent_pickups", [])
        recent_text = ", ".join(recent[-4:]) if recent else "None recorded"

        left_rows = [
            ("Guild", guild["name"]),
            ("Style", guild["style"]),
            ("Tagline", guild["tagline"]),
        ]

        middle_rows = [
            ("Roster Size", len(guild["roster"])),
            ("Total Power", guild_power(guild)),
            ("Total Signings", guild.get("total_signings", 0)),
        ]

        right_rows = [
            ("Class Preference", guild.get("class_preference") or "None"),
            ("Recent Pickups", recent_text),
        ]

        KeyValueGrid(
            rows=left_rows,
            columns=1,
            column_width=340,
            row_gap=10,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=True,
            value_bold=False,
            font_size=22,
            line_spacing=2,
        ).draw(screen, self.font, left_x, top_y)

        KeyValueGrid(
            rows=middle_rows,
            columns=1,
            column_width=340,
            row_gap=10,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=True,
            value_bold=False,
            font_size=22,
            line_spacing=2,
        ).draw(screen, self.font, middle_x, top_y)

        KeyValueGrid(
            rows=right_rows,
            columns=1,
            column_width=360,
            row_gap=10,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=True,
            value_bold=False,
            font_size=22,
            line_spacing=2,
        ).draw(screen, self.font, right_x, top_y)

    def draw_history(self, screen):
        history = recent_market_history(self.state, limit=16)
        if not history:
            history = ["No market activity recorded yet."]

        x = self.history_panel.rect.x + 18
        y = self.history_panel.rect.y + 50
        width = self.history_panel.rect.width - 36

        for entry in reversed(history):
            TextBlock(
                lines=[entry],
                color=theme.TEXT_SECONDARY,
                row_spacing=18,
                max_lines=2,
            ).draw(
                screen=screen,
                font=self.small_font,
                x=x,
                y=y,
                max_width=width,
            )
            y += 30
            if y > self.history_panel.rect.bottom - 40:
                break

    def handle_row_click(self, pos):
        guild = self.guilds_panel.item_at_pos(pos)
        if guild is not None:
            self.selected_guild = guild
            self.status_message = f"Selected rival guild: {guild['name']}"

    def build_buttons(self):
        return [
            Button((1700, 72, 140, 36), "Hub", self.on_return_to_hub),
        ]