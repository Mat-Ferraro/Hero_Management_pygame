import pygame

from pygame_ui.ui_helpers import clamp_scroll, draw_scrollbar, truncate_text, wrap_text
from systems.guild_upgrades import available_upgrades, buy_upgrade

from ..widgets.button import Button
from ..widgets.panel import Panel


class GuildUpgradesScene:
    UPGRADE_VISIBLE_ROWS = 6
    UPGRADE_ROW_SPACING = 58

    SCROLLBAR_WIDTH = 8
    SCROLLBAR_MARGIN = 14

    def __init__(self, state, on_return_to_hub, on_save_game):
        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        self.font = pygame.font.SysFont(None, 22)
        self.small_font = pygame.font.SysFont(None, 20)
        self.title_font = pygame.font.SysFont(None, 28)
        self.header_font = pygame.font.SysFont(None, 30)

        self.mouse_pos = (0, 0)
        self.status_message = "Invest in your guild."

        self.selected_upgrade_id = None
        self.upgrade_scroll = 0

        self.header_panel = Panel((20, 16, 1240, 86), "Guild Upgrades")
        self.upgrades_panel = Panel((20, 120, 720, 430), "Available Upgrades")
        self.status_panel = Panel((760, 120, 500, 430), "Guild Status")
        self.details_panel = Panel((20, 570, 1240, 135), "Upgrade Details")

        self.upgrade_row_start_y = self.upgrades_panel.rect.y + 60

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for button in self.build_buttons():
                if button.rect.collidepoint(event.pos):
                    button.on_click()
                    return

            self.handle_row_click(event.pos)

        elif event.type == pygame.MOUSEWHEEL:
            if self.upgrades_panel.rect.collidepoint(self.mouse_pos):
                self.upgrade_scroll -= event.y
                self.upgrade_scroll = clamp_scroll(
                    self.upgrade_scroll,
                    len(self.available_upgrade_rows()),
                    self.UPGRADE_VISIBLE_ROWS,
                )

    def update(self, mouse_pos):
        self.mouse_pos = mouse_pos

    def draw(self, screen):
        screen.fill((28, 28, 32))

        self.header_panel.draw(screen, self.title_font)
        self.upgrades_panel.draw(screen, self.title_font)
        self.status_panel.draw(screen, self.title_font)
        self.details_panel.draw(screen, self.title_font)

        self.draw_header(screen)
        self.draw_upgrades(screen)
        self.draw_status(screen)
        self.draw_details(screen)

        for button in self.build_buttons():
            button.update(self.mouse_pos)
            button.draw(screen, self.font)

    def draw_header(self, screen):
        upgrades = self.state.guild_upgrades

        stats = (
            f"Gold: {self.state.gold}g    "
            f"Roster: {len(self.state.roster)}/{upgrades.roster_capacity}    "
            f"Recruit Cap: Lv {upgrades.recruit_level_cap}    "
            f"Crown Stipend: {upgrades.crown_stipend}g"
        )

        screen.blit(self.header_font.render(stats, True, (235, 235, 240)), (40, 56))

        if self.status_message:
            screen.blit(
                self.font.render(self.status_message, True, (180, 200, 230)),
                (740, 82),
            )

    def draw_upgrades(self, screen):
        rows = self.visible_upgrade_rows()

        if not rows:
            screen.blit(
                self.font.render("No upgrades currently available.", True, (180, 180, 190)),
                (44, self.upgrade_row_start_y + 8),
            )
            return

        y = self.upgrade_row_start_y
        for upgrade_id, definition in rows:
            self.draw_upgrade_row(screen, upgrade_id, definition, y)
            y += self.UPGRADE_ROW_SPACING

        draw_scrollbar(
            screen=screen,
            font=self.font,
            panel=self.upgrades_panel,
            scroll=self.upgrade_scroll,
            item_count=len(self.available_upgrade_rows()),
            visible_count=self.UPGRADE_VISIBLE_ROWS,
            width=self.SCROLLBAR_WIDTH,
            margin=self.SCROLLBAR_MARGIN,
        )

    def draw_upgrade_row(self, screen, upgrade_id, definition, y):
        row_rect = self.upgrade_row_rect(y)
        is_selected = upgrade_id == self.selected_upgrade_id
        is_hovered = row_rect.collidepoint(self.mouse_pos)

        if is_selected:
            fill_color = (58, 58, 76)
            border_color = (160, 160, 220)
            border_width = 2
        elif is_hovered:
            fill_color = (52, 52, 64)
            border_color = (110, 110, 135)
            border_width = 1
        else:
            fill_color = (42, 42, 52)
            border_color = (70, 70, 86)
            border_width = 1

        pygame.draw.rect(screen, fill_color, row_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, row_rect, border_width, border_radius=8)

        name = definition["name"]
        cost = definition["cost"]
        description = definition["description"]

        screen.blit(
            self.font.render(truncate_text(f"{name} - {cost}g", self.font, 560), True, (230, 230, 240)),
            (row_rect.x + 12, row_rect.y + 8),
        )

        screen.blit(
            self.small_font.render(truncate_text(description, self.small_font, 560), True, (180, 180, 195)),
            (row_rect.x + 12, row_rect.y + 32),
        )

    def draw_status(self, screen):
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
            color = (235, 235, 240) if index == 0 else (200, 200, 215)
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

        y = 614
        for line in lines:
            for wrapped in wrap_text(line, self.small_font, 900)[:2]:
                screen.blit(self.small_font.render(wrapped, True, (210, 210, 220)), (44, y))
                y += 20

    def build_buttons(self):
        buttons = [
            Button((1120, 40, 80, 32), "Hub", self.on_return_to_hub),
        ]

        if self.selected_upgrade_id is not None:
            buttons.append(Button((1010, 642, 190, 42), "Buy Upgrade", self.buy_selected_upgrade))

        return buttons

    def handle_row_click(self, pos):
        y = self.upgrade_row_start_y
        for upgrade_id, definition in self.visible_upgrade_rows():
            if self.upgrade_row_rect(y).collidepoint(pos):
                self.selected_upgrade_id = upgrade_id
                self.status_message = f"Selected upgrade: {definition['name']}"
                return
            y += self.UPGRADE_ROW_SPACING

    def buy_selected_upgrade(self):
        if self.selected_upgrade_id is None:
            self.status_message = "Select an upgrade first."
            return

        result = buy_upgrade(self.state, self.selected_upgrade_id)
        self.status_message = result

        self.selected_upgrade_id = None
        self.upgrade_scroll = clamp_scroll(
            self.upgrade_scroll,
            len(self.available_upgrade_rows()),
            self.UPGRADE_VISIBLE_ROWS,
        )

        if self.on_save_game:
            self.on_save_game()

    def available_upgrade_rows(self):
        return available_upgrades(self.state.guild_upgrades)

    def visible_upgrade_rows(self):
        rows = self.available_upgrade_rows()
        end = self.upgrade_scroll + self.UPGRADE_VISIBLE_ROWS
        return rows[self.upgrade_scroll:end]

    def upgrade_row_rect(self, y):
        return pygame.Rect(34, y - 8, 650, 50)