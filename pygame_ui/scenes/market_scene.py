import random

from game_state import create_item_pool
from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.ui_helpers import truncate_text
from pygame_ui.widgets.details_panel import DetailsPanel
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.row_styles import draw_selectable_row
from pygame_ui.widgets.scrollable_list_panel import ScrollableListPanel

from ..widgets.button import Button


class MarketScene(SceneBase):
    REFRESH_COST = 25
    SHOP_SIZE = 8

    def __init__(self, state, on_return_to_hub, on_save_game):
        super().__init__()

        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        self.status_message = "Buy equipment for your guild."
        self.selected_shop_item = None
        self.shop_items = self.generate_shop_items()

        self.details_panel = DetailsPanel((20, 560, 1240, 145), "Market Details")

        self.shop_panel = ScrollableListPanel(
            rect=(20, 120, 620, 420),
            title="Shop Inventory",
            row_height=48,
            row_spacing=56,
            visible_rows=6,
            font=self.font,
            title_font=self.title_font,
            padding=14,
            title_height=60,
        )

        self.inventory_panel = ScrollableListPanel(
            rect=(660, 120, 600, 420),
            title="Guild Inventory",
            row_height=44,
            row_spacing=52,
            visible_rows=6,
            font=self.font,
            title_font=self.title_font,
            padding=14,
            title_height=60,
        )

    def sync_lists(self):
        self.shop_panel.set_items(self.shop_items)
        self.inventory_panel.set_items(self.state.inventory)

    def handle_event(self, event):
        self.sync_lists()

        if self.shop_panel.handle_event(event):
            return

        if self.inventory_panel.handle_event(event):
            return

        if self.handle_buttons_click(event, self.build_buttons()):
            return

        if self.is_left_click(event):
            self.handle_row_click(event.pos)

    def update(self, mouse_pos):
        super().update(mouse_pos)
        self.sync_lists()
        self.shop_panel.update(mouse_pos)
        self.inventory_panel.update(mouse_pos)

    def draw(self, screen):
        self.sync_lists()
        self.clear_screen(screen)

        self.draw_header(screen)

        self.shop_panel.draw(
            screen=screen,
            row_drawer=self.draw_shop_row,
            selected_item=self.selected_shop_item,
            empty_text="The shop is empty.",
        )

        self.inventory_panel.draw(
            screen=screen,
            row_drawer=self.draw_inventory_row,
            selected_item=None,
            empty_text="No owned items.",
        )

        self.draw_details(screen)
        self.update_and_draw_buttons(screen, self.build_buttons())

    def draw_header(self, screen):
        stats = (
            f"Gold: {self.state.gold}g    "
            f"Shop Items: {len(self.shop_items)}    "
            f"Inventory: {len(self.state.inventory)}    "
            f"Refresh Cost: {self.REFRESH_COST}g"
        )

        HeaderPanel(
            title="Market",
            stats=stats,
            status_message=self.status_message,
        ).draw(screen, self.title_font, self.header_font, self.font)

    def draw_shop_row(self, screen, item, row_rect, is_selected, is_hovered):
        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style="dark",
        )

        price = self.item_price(item)

        line_1 = truncate_text(
            f"{item.name} [{item.rarity} {item.slot}]",
            self.font,
            row_rect.width - 100,
        )
        line_2 = truncate_text(
            self.item_bonus_summary(item),
            self.small_font,
            row_rect.width - 100,
        )

        screen.blit(self.font.render(line_1, True, theme.TEXT_PRIMARY), (row_rect.x + 12, row_rect.y + 7))
        screen.blit(self.small_font.render(line_2, True, theme.TEXT_MUTED), (row_rect.x + 12, row_rect.y + 30))
        screen.blit(self.font.render(f"{price}g", True, (235, 220, 160)), (row_rect.right - 76, row_rect.y + 17))

    def draw_inventory_row(self, screen, item, row_rect, is_selected, is_hovered):
        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=False,
            is_hovered=is_hovered,
            style="green",
        )

        line_1 = truncate_text(
            f"{item.name} [{item.rarity} {item.slot}]",
            self.font,
            row_rect.width - 24,
        )
        line_2 = truncate_text(
            f"Value {item.value}g",
            self.small_font,
            row_rect.width - 24,
        )

        screen.blit(self.font.render(line_1, True, (210, 240, 210)), (row_rect.x + 12, row_rect.y + 8))
        screen.blit(self.small_font.render(line_2, True, (180, 210, 180)), (row_rect.x + 12, row_rect.y + 29))

    def draw_details(self, screen):
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
            Button((800, 642, 190, 42), "Refresh Shop", self.refresh_shop),
        ]

        if self.selected_shop_item is not None:
            buttons.append(Button(theme.DETAIL_ACTION_BUTTON_RECT, "Buy Item", self.buy_selected_item))

        return buttons

    def handle_row_click(self, pos):
        item = self.shop_panel.item_at_pos(pos)
        if item is not None:
            self.selected_shop_item = item
            self.status_message = f"Selected shop item: {item.name}"

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
        self.sync_lists()

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
        self.sync_lists()

        if self.on_save_game:
            self.on_save_game()

        self.status_message = f"Shop refreshed for {self.REFRESH_COST}g."

    def generate_shop_items(self):
        item_pool = create_item_pool()
        if not item_pool:
            return []

        return [self.clone_market_item(random.choice(item_pool)) for _ in range(self.SHOP_SIZE)]

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