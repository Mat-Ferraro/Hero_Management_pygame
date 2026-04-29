import random
import pygame

from game_state import create_item_pool
from pygame_ui.ui_helpers import clamp_scroll, draw_scrollbar, truncate_text, wrap_text

from ..widgets.button import Button
from ..widgets.panel import Panel


class MarketScene:
    SHOP_VISIBLE_ROWS = 6
    INVENTORY_VISIBLE_ROWS = 6

    SHOP_ROW_SPACING = 56
    INVENTORY_ROW_SPACING = 52

    SCROLLBAR_WIDTH = 8
    SCROLLBAR_MARGIN = 14

    REFRESH_COST = 25
    SHOP_SIZE = 8

    def __init__(self, state, on_return_to_hub, on_save_game):
        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        self.font = pygame.font.SysFont(None, 22)
        self.small_font = pygame.font.SysFont(None, 20)
        self.title_font = pygame.font.SysFont(None, 28)
        self.header_font = pygame.font.SysFont(None, 30)

        self.mouse_pos = (0, 0)
        self.status_message = "Buy equipment for your guild."

        self.selected_shop_item = None
        self.shop_scroll = 0
        self.inventory_scroll = 0

        self.shop_items = self.generate_shop_items()

        self.header_panel = Panel((20, 16, 1240, 86), "Market")
        self.shop_panel = Panel((20, 120, 620, 420), "Shop Inventory")
        self.inventory_panel = Panel((660, 120, 600, 420), "Guild Inventory")
        self.details_panel = Panel((20, 560, 1240, 145), "Market Details")

        self.shop_row_start_y = self.shop_panel.rect.y + 60
        self.inventory_row_start_y = self.inventory_panel.rect.y + 60

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for button in self.build_buttons():
                if button.rect.collidepoint(event.pos):
                    button.on_click()
                    return

            self.handle_row_click(event.pos)

        elif event.type == pygame.MOUSEWHEEL:
            self.handle_mouse_wheel(event)

    def handle_mouse_wheel(self, event):
        if self.shop_panel.rect.collidepoint(self.mouse_pos):
            self.shop_scroll -= event.y
            self.shop_scroll = clamp_scroll(
                self.shop_scroll,
                len(self.shop_items),
                self.SHOP_VISIBLE_ROWS,
            )

        elif self.inventory_panel.rect.collidepoint(self.mouse_pos):
            self.inventory_scroll -= event.y
            self.inventory_scroll = clamp_scroll(
                self.inventory_scroll,
                len(self.state.inventory),
                self.INVENTORY_VISIBLE_ROWS,
            )

    def update(self, mouse_pos):
        self.mouse_pos = mouse_pos

    def draw(self, screen):
        screen.fill((28, 28, 32))

        self.header_panel.draw(screen, self.title_font)
        self.shop_panel.draw(screen, self.title_font)
        self.inventory_panel.draw(screen, self.title_font)
        self.details_panel.draw(screen, self.title_font)

        self.draw_header(screen)
        self.draw_shop(screen)
        self.draw_inventory(screen)
        self.draw_details(screen)

        for button in self.build_buttons():
            button.update(self.mouse_pos)
            button.draw(screen, self.font)

    def draw_header(self, screen):
        stats = (
            f"Gold: {self.state.gold}g    "
            f"Shop Items: {len(self.shop_items)}    "
            f"Inventory: {len(self.state.inventory)}    "
            f"Refresh Cost: {self.REFRESH_COST}g"
        )

        screen.blit(self.header_font.render(stats, True, (235, 235, 240)), (40, 56))

        if self.status_message:
            screen.blit(
                self.font.render(self.status_message, True, (180, 200, 230)),
                (740, 82),
            )

    def draw_shop(self, screen):
        visible = self.visible_shop_items()

        if not visible:
            screen.blit(
                self.font.render("The shop is empty.", True, (180, 180, 190)),
                (44, self.shop_row_start_y + 8),
            )
            self.draw_panel_scrollbar(
                screen,
                self.shop_panel,
                self.shop_scroll,
                len(self.shop_items),
                self.SHOP_VISIBLE_ROWS,
            )
            return

        y = self.shop_row_start_y
        for item in visible:
            self.draw_shop_row(screen, item, y)
            y += self.SHOP_ROW_SPACING

        self.draw_panel_scrollbar(
            screen,
            self.shop_panel,
            self.shop_scroll,
            len(self.shop_items),
            self.SHOP_VISIBLE_ROWS,
        )

    def draw_shop_row(self, screen, item, y):
        row_rect = self.shop_row_rect(y)
        is_selected = item is self.selected_shop_item
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

        line_1 = truncate_text(f"{item.name} [{item.rarity} {item.slot}]", self.font, 390)
        line_2 = truncate_text(self.item_bonus_summary(item), self.small_font, 390)
        price = self.item_price(item)

        screen.blit(self.font.render(line_1, True, (230, 230, 240)), (row_rect.x + 12, row_rect.y + 7))
        screen.blit(self.small_font.render(line_2, True, (180, 180, 195)), (row_rect.x + 12, row_rect.y + 30))
        screen.blit(self.font.render(f"{price}g", True, (235, 220, 160)), (row_rect.right - 76, row_rect.y + 17))

    def draw_inventory(self, screen):
        visible = self.visible_inventory_items()

        if not visible:
            screen.blit(
                self.font.render("No owned items.", True, (180, 180, 190)),
                (684, self.inventory_row_start_y + 8),
            )
            self.draw_panel_scrollbar(
                screen,
                self.inventory_panel,
                self.inventory_scroll,
                len(self.state.inventory),
                self.INVENTORY_VISIBLE_ROWS,
            )
            return

        y = self.inventory_row_start_y
        for item in visible:
            self.draw_inventory_row(screen, item, y)
            y += self.INVENTORY_ROW_SPACING

        self.draw_panel_scrollbar(
            screen,
            self.inventory_panel,
            self.inventory_scroll,
            len(self.state.inventory),
            self.INVENTORY_VISIBLE_ROWS,
        )

    def draw_inventory_row(self, screen, item, y):
        row_rect = self.inventory_row_rect(y)
        is_hovered = row_rect.collidepoint(self.mouse_pos)

        fill_color = (48, 64, 52) if is_hovered else (42, 54, 44)
        border_color = (100, 150, 110) if is_hovered else (72, 96, 76)

        pygame.draw.rect(screen, fill_color, row_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, row_rect, 1, border_radius=8)

        line_1 = truncate_text(f"{item.name} [{item.rarity} {item.slot}]", self.font, 500)
        line_2 = truncate_text(f"Value {item.value}g", self.small_font, 500)

        screen.blit(self.font.render(line_1, True, (210, 240, 210)), (row_rect.x + 12, row_rect.y + 8))
        screen.blit(self.small_font.render(line_2, True, (180, 210, 180)), (row_rect.x + 12, row_rect.y + 29))

    def draw_details(self, screen):
        left_x = 44
        y = 606

        if self.selected_shop_item is None:
            lines = [
                "Select a shop item to inspect it.",
                "Buying moves the item into guild inventory.",
                f"Refreshing the shop costs {self.REFRESH_COST}g.",
            ]
        else:
            item = self.selected_shop_item
            lines = [
                f"Item: {item.name}",
                f"Slot: {item.slot}    Rarity: {item.rarity}    Price: {self.item_price(item)}g",
                f"Bonuses: {self.item_bonus_summary(item)}",
                f"Classes: {', '.join(item.class_restrictions) if item.class_restrictions else 'Any'}",
            ]

        for line in lines[:2]:
            screen.blit(self.small_font.render(line, True, (210, 210, 220)), (left_x, y))
            y += 20

        if len(lines) > 2:
            for wrapped_line in wrap_text(lines[2], self.small_font, 900)[:4]:
                screen.blit(self.small_font.render(wrapped_line, True, (210, 210, 220)), (left_x, y))
                y += 20

        if len(lines) > 3:
            screen.blit(self.small_font.render(lines[3], True, (210, 210, 220)), (left_x, y))

    def build_buttons(self):
        buttons = [
            Button((1120, 40, 80, 32), "Hub", self.on_return_to_hub),
            Button((800, 642, 190, 42), "Refresh Shop", self.refresh_shop),
        ]

        if self.selected_shop_item is not None:
            buttons.append(Button((1010, 642, 190, 42), "Buy Item", self.buy_selected_item))

        return buttons

    def handle_row_click(self, pos):
        y = self.shop_row_start_y
        for item in self.visible_shop_items():
            if self.shop_row_rect(y).collidepoint(pos):
                self.selected_shop_item = item
                self.status_message = f"Selected shop item: {item.name}"
                return
            y += self.SHOP_ROW_SPACING

    def buy_selected_item(self):
        if self.selected_shop_item is None:
            self.status_message = "Select an item first."
            return

        item = self.selected_shop_item
        price = self.item_price(item)

        if self.state.gold < price:
            self.status_message = f"Not enough gold. {item.name} costs {price}g."
            return

        if item not in self.shop_items:
            self.status_message = "That item is no longer available."
            self.selected_shop_item = None
            return

        self.state.gold -= price
        self.shop_items.remove(item)
        self.state.inventory.append(item)

        self.selected_shop_item = None

        self.shop_scroll = clamp_scroll(
            self.shop_scroll,
            len(self.shop_items),
            self.SHOP_VISIBLE_ROWS,
        )

        self.inventory_scroll = clamp_scroll(
            self.inventory_scroll,
            len(self.state.inventory),
            self.INVENTORY_VISIBLE_ROWS,
        )

        if self.on_save_game:
            self.on_save_game()

        self.status_message = f"Bought {item.name} for {price}g."

    def refresh_shop(self):
        if self.state.gold < self.REFRESH_COST:
            self.status_message = f"Not enough gold to refresh shop. Cost: {self.REFRESH_COST}g."
            return

        self.state.gold -= self.REFRESH_COST
        self.shop_items = self.generate_shop_items()
        self.selected_shop_item = None
        self.shop_scroll = 0

        if self.on_save_game:
            self.on_save_game()

        self.status_message = f"Shop refreshed for {self.REFRESH_COST}g."

    def generate_shop_items(self):
        item_pool = create_item_pool()
        if not item_pool:
            return []

        generated = []
        for _ in range(self.SHOP_SIZE):
            generated.append(self.clone_market_item(random.choice(item_pool)))

        return generated

    def clone_market_item(self, item):
        from models import Item

        return Item(
            name=item.name,
            slot=item.slot,
            stat_bonuses=dict(item.stat_bonuses),
            value=item.value,
            rarity=item.rarity,
            damage_type_bonus=dict(item.damage_type_bonus),
            enemy_type_bonus=dict(item.enemy_type_bonus),
            enemy_type_resistance=dict(item.enemy_type_resistance),
            class_restrictions=list(item.class_restrictions),
            enemy_affinity=list(item.enemy_affinity),
        )

    def item_price(self, item):
        rarity_multiplier = {
            "Common": 1.0,
            "Uncommon": 1.25,
            "Rare": 1.6,
            "Epic": 2.1,
            "Legendary": 3.0,
        }.get(item.rarity, 1.0)

        return max(1, int(item.value * rarity_multiplier))

    def item_bonus_summary(self, item):
        parts = []

        for stat, value in item.stat_bonuses.items():
            parts.append(f"+{value} {stat}")

        for damage, value in item.damage_type_bonus.items():
            parts.append(f"+{int(value * 100)}% {damage} dmg")

        for enemy, value in item.enemy_type_bonus.items():
            parts.append(f"+{int(value * 100)}% vs {enemy}")

        for enemy, value in item.enemy_type_resistance.items():
            parts.append(f"-{int(value * 100)}% dmg from {enemy}")

        return "; ".join(parts) if parts else "No bonuses"

    def visible_shop_items(self):
        end = self.shop_scroll + self.SHOP_VISIBLE_ROWS
        return self.shop_items[self.shop_scroll:end]

    def visible_inventory_items(self):
        end = self.inventory_scroll + self.INVENTORY_VISIBLE_ROWS
        return self.state.inventory[self.inventory_scroll:end]

    def draw_panel_scrollbar(self, screen, panel, scroll, item_count, visible_count):
        draw_scrollbar(
            screen=screen,
            font=self.font,
            panel=panel,
            scroll=scroll,
            item_count=item_count,
            visible_count=visible_count,
            width=self.SCROLLBAR_WIDTH,
            margin=self.SCROLLBAR_MARGIN,
        )

    def shop_row_rect(self, y):
        return pygame.Rect(34, y - 8, 580, 48)

    def inventory_row_rect(self, y):
        return pygame.Rect(674, y - 8, 550, 44)