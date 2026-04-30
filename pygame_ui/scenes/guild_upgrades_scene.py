from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.key_value_grid import KeyValueGrid
from pygame_ui.widgets.label_value_text import LabelValueText
from pygame_ui.widgets.navigation_buttons import action_button, hub_button
from pygame_ui.widgets.resource_header import ResourceHeader
from pygame_ui.widgets.section_title import SectionTitle
from pygame_ui.widgets.selection_details_panel import SelectionDetailsPanel
from pygame_ui.widgets.status_chip import StatusChip
from pygame_ui.widgets.text_block import TextBlock
from pygame_ui.widgets.row_styles import draw_selectable_row
from pygame_ui.widgets.scrollable_list_panel import ScrollableListPanel
from systems.guild_upgrades import available_upgrades, buy_upgrade


class GuildUpgradesScene(SceneBase):
    def __init__(self, state, on_return_to_hub, on_save_game):
        super().__init__()

        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        self.status_message = "Invest in your guild."
        self.selected_upgrade_id = None

        self.details_panel = SelectionDetailsPanel(
            rect=(40, 780, 1840, 240),
            title="Upgrade Details",
            empty_message="Select an upgrade to inspect it.",
            left_width=520,
            right_width=1120,
        )

        self.upgrades_panel = ScrollableListPanel(
            rect=(40, 150, 1080, 590),
            title="Available Upgrades",
            row_height=70,
            row_gap=10,
            visible_rows=None,
            font=self.font,
            title_font=self.title_font,
            padding=18,
            title_height=64,
        )

        self.status_rect = (1160, 150, 720, 590)

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
            rect=(40, 30, 1840, 96),
            title="Guild Upgrades",
            stats="",
            status_message=self.status_message,
            stats_pos=(70, 70),
            status_pos=(1060, 108),
        ).draw(screen, self.title_font, self.header_font, self.font)

        ResourceHeader(
            resources=[
                ("Gold", f"{self.state.gold}g"),
                ("Roster", f"{len(self.state.roster)}/{upgrades.roster_capacity}"),
                ("Recruit", f"Lv {upgrades.recruit_level_cap}"),
                ("Stipend", f"{upgrades.crown_stipend}g"),
                ("Training", f"Lv {upgrades.training_hall_level}"),
            ],
            spacing=190,
            item_max_width=170,
            font_size=24,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=False,
            value_bold=True,
        ).draw(screen, self.font, 60, 72)

    def draw_upgrade_row(self, screen, row, row_rect, is_selected, is_hovered):
        _upgrade_id, definition = row

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
            (row_rect.x + 14, row_rect.y + 10),
        )

        StatusChip(
            rect=(row_rect.right - 106, row_rect.y + 10, 90, 26),
            text=f"{cost}g",
            style="warning" if cost > self.state.gold else "good",
        ).draw(screen, self.small_font)

        TextBlock(
            lines=[description],
            color=theme.TEXT_MUTED,
            row_spacing=18,
            max_lines=2,
        ).draw(
            screen=screen,
            font=self.small_font,
            x=row_rect.x + 14,
            y=row_rect.y + 40,
            max_width=row_rect.width - 130,
        )

    def draw_status(self, screen):
        from pygame_ui.widgets.card import Card

        Card(
            rect=self.status_rect,
            title="Guild Status",
            lines=[],
            fill_color=theme.PANEL_BG,
            border_color=theme.PANEL_BORDER,
            padding=18,
        ).draw(screen, self.title_font, self.font)

        upgrades = self.state.guild_upgrades

        SectionTitle(
            "Current Capabilities",
            "Your infrastructure defines your long-term growth ceiling.",
        ).draw(
            screen=screen,
            title_font=self.font,
            subtitle_font=self.small_font,
            x=1190,
            y=206,
        )

        KeyValueGrid(
            rows=[
                ("Roster", f"{len(self.state.roster)}/{upgrades.roster_capacity}"),
                ("Classes", ", ".join(upgrades.unlocked_classes)),
                ("Recruit Cap", f"Lv {upgrades.recruit_level_cap}"),
                ("Market", "Unlocked" if upgrades.market_unlocked else "Locked"),
                ("Rarity Cap", upgrades.market_rarity_cap),
                ("Mission Cap", f"Diff {upgrades.mission_difficulty_cap}"),
                ("Stipend", f"{upgrades.crown_stipend}g"),
                ("Training", f"Lv {upgrades.training_hall_level}"),
            ],
            columns=1,
            column_width=500,
            row_gap=12,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=True,
            value_bold=False,
            font_size=22,
            line_spacing=2,
        ).draw(
            screen=screen,
            font=self.font,
            x=1190,
            y=270,
        )

        chips = [
            ("Market", "good" if upgrades.market_unlocked else "locked"),
            ("Training", "good" if upgrades.training_hall_level > 0 else "locked"),
            (f"Mission {upgrades.mission_difficulty_cap}", "info"),
            (f"Roster {upgrades.roster_capacity}", "info"),
            (f"Recruit Lv {upgrades.recruit_level_cap}", "info"),
        ]

        start_x = 1190
        start_y = 560
        chip_height = 30
        chip_gap_x = 12
        chip_gap_y = 12
        max_row_width = 620

        current_x = start_x
        current_y = start_y

        for label, style in chips:
            chip_width = max(132, 36 + len(label) * 8)

            if current_x > start_x and (current_x - start_x + chip_width) > max_row_width:
                current_x = start_x
                current_y += chip_height + chip_gap_y

            StatusChip(
                (current_x, current_y, chip_width, chip_height),
                label,
                style,
            ).draw(screen, self.small_font)

            current_x += chip_width + chip_gap_x

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
                max_width=1200,
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
            "Guild upgrades permanently improve your strategic options.",
            "Some upgrades unlock new screens or services, while others raise limits and scaling.",
        ]

        self.details_panel.draw(
            screen=screen,
            title_font=self.title_font,
            font=self.font,
            left_lines=left_lines,
            right_lines=right_lines,
        )

    def build_buttons(self):
        buttons = [
            hub_button(self.on_return_to_hub, text="Hub"),
        ]

        if self.selected_upgrade_id is not None:
            buttons.append(
                action_button(
                    "Buy Upgrade",
                    self.buy_selected_upgrade,
                    rect=(1660, 958, 180, 44),
                )
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