from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.widgets.details_panel import DetailsPanel
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.row_styles import draw_selectable_row
from pygame_ui.widgets.scrollable_list_panel import ScrollableListPanel
from systems.guild_upgrades import available_upgrades, buy_upgrade

from ..widgets.button import Button
from ..widgets.panel import Panel


class GuildUpgradesScene(SceneBase):
    def __init__(self, state, on_return_to_hub, on_save_game):
        super().__init__()

        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        self.status_message = "Invest in your guild."
        self.selected_upgrade_id = None

        self.status_panel = Panel((760, 120, 500, 430), "Guild Status")
        self.details_panel = DetailsPanel((20, 570, 1240, 135), "Upgrade Details")

        self.upgrades_panel = ScrollableListPanel(
            rect=(20, 120, 720, 430),
            title="Available Upgrades",
            row_height=50,
            row_spacing=58,
            visible_rows=6,
            font=self.font,
            title_font=self.title_font,
            padding=14,
            title_height=60,
        )

    def sync_lists(self):
        self.upgrades_panel.set_items(self.available_upgrade_rows())

    def handle_event(self, event):
        self.sync_lists()

        if self.upgrades_panel.handle_event(event):
            return

        if self.handle_buttons_click(event, self.build_buttons()):
            return

        if self.is_left_click(event):
            self.handle_row_click(event.pos)

    def update(self, mouse_pos):
        super().update(mouse_pos)
        self.sync_lists()
        self.upgrades_panel.update(mouse_pos)

    def draw(self, screen):
        self.sync_lists()
        self.clear_screen(screen)

        self.draw_header(screen)

        self.upgrades_panel.draw(
            screen=screen,
            row_drawer=self.draw_upgrade_row,
            selected_item=self.selected_upgrade_row(),
            empty_text="No upgrades currently available.",
        )

        self.draw_status(screen)
        self.draw_details(screen)
        self.update_and_draw_buttons(screen, self.build_buttons())

    def draw_header(self, screen):
        upgrades = self.state.guild_upgrades

        stats = (
            f"Gold: {self.state.gold}g    "
            f"Roster: {len(self.state.roster)}/{upgrades.roster_capacity}    "
            f"Recruit Cap: Lv {upgrades.recruit_level_cap}    "
            f"Crown Stipend: {upgrades.crown_stipend}g"
        )

        HeaderPanel(
            title="Guild Upgrades",
            stats=stats,
            status_message=self.status_message,
        ).draw(screen, self.title_font, self.header_font, self.font)

    def draw_upgrade_row(self, screen, row, row_rect, is_selected, is_hovered):
        upgrade_id, definition = row

        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style="dark",
        )

        name = definition["name"]
        cost = definition["cost"]
        description = definition["description"]

        screen.blit(
            self.font.render(f"{name} - {cost}g", True, theme.TEXT_PRIMARY),
            (row_rect.x + 12, row_rect.y + 8),
        )

        screen.blit(
            self.small_font.render(description[:86], True, theme.TEXT_MUTED),
            (row_rect.x + 12, row_rect.y + 32),
        )

    def draw_status(self, screen):
        self.status_panel.draw(screen, self.title_font)

        upgrades = self.state.guild_upgrades

        lines = [
            "Current Guild Capabilities",
            f"Roster Capacity: {len(self.state.roster)}/{upgrades.roster_capacity}",
            f"Unlocked Classes: {', '.join(upgrades.unlocked_classes)}",
            f"Recruit Level Cap: {upgrades.recruit_level_cap}",
            f"Market: {'Unlocked' if upgrades.market_unlocked else 'Locked'}",
            f"Market Rarity Cap: {upgrades.market_rarity_cap}",
            f"Mission Difficulty Cap: {upgrades.mission_difficulty_cap}",
            f"Crown Stipend: {upgrades.crown_stipend}g / campaign",
        ]

        y = 178
        for index, line in enumerate(lines):
            color = theme.TEXT_PRIMARY if index == 0 else theme.TEXT_SECONDARY
            screen.blit(self.font.render(line, True, color), (790, y))
            y += 30

    def draw_details(self, screen):
        if self.selected_upgrade_id is None:
            lines = [
                "Select an upgrade to inspect it.",
                "Guild upgrades are your main tycoon progression layer.",
            ]
        else:
            definition = dict(self.available_upgrade_rows()).get(self.selected_upgrade_id)
            if definition is None:
                lines = ["Selected upgrade is no longer available."]
            else:
                lines = [
                    f"{definition['name']} - {definition['cost']}g",
                    definition["description"],
                ]

        self.details_panel.draw_lines(
            screen=screen,
            title_font=self.title_font,
            font=self.small_font,
            lines=lines,
            max_width=900,
        )

    def build_buttons(self):
        buttons = [
            Button(theme.HUB_BUTTON_RECT, "Hub", self.on_return_to_hub),
        ]

        if self.selected_upgrade_id is not None:
            buttons.append(
                Button(theme.DETAIL_ACTION_BUTTON_RECT, "Buy Upgrade", self.buy_selected_upgrade)
            )

        return buttons

    def handle_row_click(self, pos):
        row = self.upgrades_panel.item_at_pos(pos)
        if row is None:
            return

        upgrade_id, definition = row
        self.selected_upgrade_id = upgrade_id
        self.status_message = f"Selected upgrade: {definition['name']}"

    def buy_selected_upgrade(self):
        if self.selected_upgrade_id is None:
            self.status_message = "Select an upgrade first."
            return

        result = buy_upgrade(self.state, self.selected_upgrade_id)
        self.status_message = result
        self.selected_upgrade_id = None
        self.sync_lists()

        if self.on_save_game:
            self.on_save_game()

    def available_upgrade_rows(self):
        return available_upgrades(self.state.guild_upgrades)

    def selected_upgrade_row(self):
        if self.selected_upgrade_id is None:
            return None

        for row in self.available_upgrade_rows():
            if row[0] == self.selected_upgrade_id:
                return row

        return None