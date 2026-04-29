from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.key_value_grid import KeyValueGrid
from pygame_ui.widgets.navigation_buttons import action_button, hub_button
from pygame_ui.widgets.resource_header import ResourceHeader
from pygame_ui.widgets.section_title import SectionTitle
from pygame_ui.widgets.selection_details_panel import SelectionDetailsPanel
from pygame_ui.widgets.status_chip import StatusChip
from pygame_ui.widgets.text_block import TextBlock
from pygame_ui.widgets.row_styles import draw_selectable_row
from pygame_ui.widgets.scrollable_list_panel import ScrollableListPanel
from systems.guild_upgrades import available_upgrades, buy_upgrade

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

        self.details_panel = SelectionDetailsPanel(
            rect=(20, 570, 1240, 135),
            title="Upgrade Details",
            empty_message="Select an upgrade to inspect it.",
            left_width=560,
            right_width=560,
        )

        self.upgrades_panel = ScrollableListPanel(
            rect=(20, 120, 720, 430),
            title="Available Upgrades",
            row_height=58,
            row_gap=8,
            visible_rows=None,
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

        HeaderPanel(
            title="Guild Upgrades",
            stats="",
            status_message=self.status_message,
        ).draw(screen, self.title_font, self.header_font, self.font)

        ResourceHeader(
            resources=[
                ("Gold", f"{self.state.gold}g"),
                ("Roster", f"{len(self.state.roster)}/{upgrades.roster_capacity}"),
                ("Recruit", f"Lv {upgrades.recruit_level_cap}"),
                ("Stipend", f"{upgrades.crown_stipend}g"),
            ],
            spacing=185,
        ).draw(screen, self.font, 40, 58)

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
            self.font.render(name, True, theme.TEXT_PRIMARY),
            (row_rect.x + 12, row_rect.y + 8),
        )

        StatusChip(
            rect=(row_rect.right - 92, row_rect.y + 8, 78, 24),
            text=f"{cost}g",
            style="warning" if cost > self.state.gold else "good",
        ).draw(screen, self.small_font)

        TextBlock(
            lines=[description],
            color=theme.TEXT_MUTED,
            row_spacing=18,
            max_lines=1,
        ).draw(
            screen=screen,
            font=self.small_font,
            x=row_rect.x + 12,
            y=row_rect.y + 36,
            max_width=row_rect.width - 120,
        )

    def draw_status(self, screen):
        self.status_panel.draw(screen, self.title_font)

        upgrades = self.state.guild_upgrades

        SectionTitle(
            "Current Capabilities",
            "Your guild infrastructure determines long-term growth.",
        ).draw(
            screen=screen,
            title_font=self.font,
            subtitle_font=self.small_font,
            x=790,
            y=174,
        )

        grid_rows = [
            ("Roster", f"{len(self.state.roster)}/{upgrades.roster_capacity}"),
            ("Classes", ", ".join(upgrades.unlocked_classes)),
            ("Recruit Cap", f"Lv {upgrades.recruit_level_cap}"),
            ("Market", "Unlocked" if upgrades.market_unlocked else "Locked"),
            ("Rarity Cap", upgrades.market_rarity_cap),
            ("Mission Cap", f"Diff {upgrades.mission_difficulty_cap}"),
            ("Stipend", f"{upgrades.crown_stipend}g"),
            ("Training", f"Lv {upgrades.training_hall_level}"),
        ]

        KeyValueGrid(
            rows=grid_rows,
            columns=1,
            label_width=120,
            column_width=430,
            row_spacing=24,
        ).draw(
            screen=screen,
            font=self.small_font,
            x=790,
            y=235,
        )

        self.draw_unlock_chips(screen, upgrades)

    def draw_unlock_chips(self, screen, upgrades):
        y = 498
        x = 790

        chips = [
            ("Market", "good" if upgrades.market_unlocked else "locked"),
            ("Training", "good" if upgrades.training_hall_level > 0 else "locked"),
            (f"Mission {upgrades.mission_difficulty_cap}", "info"),
            (f"Roster {upgrades.roster_capacity}", "info"),
        ]

        for label, style in chips:
            StatusChip((x, y, 105, 26), label, style).draw(screen, self.small_font)
            x += 115

    def draw_details(self, screen):
        if self.selected_upgrade_id is None:
            self.details_panel.draw(
                screen=screen,
                title_font=self.title_font,
                font=self.small_font,
                left_lines=[],
                right_lines=[],
            )
            return

        definition = dict(self.available_upgrade_rows()).get(self.selected_upgrade_id)
        if definition is None:
            self.details_panel.draw_lines(
                screen=screen,
                title_font=self.title_font,
                font=self.small_font,
                lines=["Selected upgrade is no longer available."],
                max_width=900,
            )
            return

        cost = definition["cost"]
        can_afford = self.state.gold >= cost

        left_lines = [
            f"Upgrade: {definition['name']}",
            f"Cost: {cost}g",
            f"Status: {'Affordable' if can_afford else 'Not enough gold'}",
        ]

        right_lines = [
            definition["description"],
        ]

        self.details_panel.draw(
            screen=screen,
            title_font=self.title_font,
            font=self.small_font,
            left_lines=left_lines,
            right_lines=right_lines,
        )

    def build_buttons(self):
        buttons = [
            hub_button(self.on_return_to_hub),
        ]

        if self.selected_upgrade_id is not None:
            buttons.append(action_button("Buy Upgrade", self.buy_selected_upgrade))

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