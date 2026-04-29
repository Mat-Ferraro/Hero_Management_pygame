import pygame

from pygame_ui.ui_helpers import clamp_scroll, draw_scrollbar, truncate_text, wrap_text

from ..widgets.button import Button
from ..widgets.panel import Panel


class InventoryScene:
    ITEM_VISIBLE_ROWS = 5
    HERO_VISIBLE_ROWS = 5
    EQUIPMENT_VISIBLE_ROWS = 3

    ITEM_ROW_SPACING = 52
    HERO_ROW_SPACING = 52
    EQUIPMENT_ROW_SPACING = 34

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
        self.status_message = "Select an item and a hero."

        self.selected_item = None
        self.selected_hero = None
        self.selected_equipment_slot = None

        self.item_scroll = 0
        self.hero_scroll = 0
        self.equipment_scroll = 0

        self.header_panel = Panel((20, 16, 1240, 86), "Inventory")
        self.items_panel = Panel((20, 120, 520, 380), "Items")
        self.heroes_panel = Panel((560, 120, 700, 270), "Heroes")
        self.equipment_panel = Panel((560, 410, 700, 90), "Selected Hero Equipment")
        self.details_panel = Panel((20, 520, 1240, 185), "Selection Details")

        self.item_row_start_y = self.items_panel.rect.y + 60
        self.hero_row_start_y = self.heroes_panel.rect.y + 60
        self.equipment_row_start_y = self.equipment_panel.rect.y + 38

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
        if self.items_panel.rect.collidepoint(self.mouse_pos):
            self.item_scroll -= event.y
            self.item_scroll = clamp_scroll(
                self.item_scroll,
                len(self.state.inventory),
                self.ITEM_VISIBLE_ROWS,
            )

        elif self.heroes_panel.rect.collidepoint(self.mouse_pos):
            self.hero_scroll -= event.y
            self.hero_scroll = clamp_scroll(
                self.hero_scroll,
                len(self.state.roster),
                self.HERO_VISIBLE_ROWS,
            )

        elif self.equipment_panel.rect.collidepoint(self.mouse_pos):
            self.equipment_scroll -= event.y
            self.equipment_scroll = clamp_scroll(
                self.equipment_scroll,
                len(self.selected_hero_equipment_rows()),
                self.EQUIPMENT_VISIBLE_ROWS,
            )

    def update(self, mouse_pos):
        self.mouse_pos = mouse_pos

    def draw(self, screen):
        screen.fill((28, 28, 32))

        self.header_panel.draw(screen, self.title_font)
        self.items_panel.draw(screen, self.title_font)
        self.heroes_panel.draw(screen, self.title_font)
        self.equipment_panel.draw(screen, self.title_font)
        self.details_panel.draw(screen, self.title_font)

        self.draw_header(screen)
        self.draw_items(screen)
        self.draw_heroes(screen)
        self.draw_equipment(screen)
        self.draw_details(screen)

        for button in self.build_buttons():
            button.update(self.mouse_pos)
            button.draw(screen, self.font)

    def draw_header(self, screen):
        stats = (
            f"Gold: {self.state.gold}g    "
            f"Roster: {len(self.state.roster)}    "
            f"Inventory: {len(self.state.inventory)}"
        )

        screen.blit(self.header_font.render(stats, True, (235, 235, 240)), (40, 56))

        if self.status_message:
            screen.blit(
                self.font.render(self.status_message, True, (180, 200, 230)),
                (740, 82),
            )

    def draw_items(self, screen):
        visible = self.visible_items()

        if not visible:
            screen.blit(
                self.font.render("No items in inventory.", True, (180, 180, 190)),
                (44, self.item_row_start_y + 8),
            )
            self.draw_panel_scrollbar(
                screen,
                self.items_panel,
                self.item_scroll,
                len(self.state.inventory),
                self.ITEM_VISIBLE_ROWS,
            )
            return

        y = self.item_row_start_y
        for item in visible:
            self.draw_item_row(screen, item, y)
            y += self.ITEM_ROW_SPACING

        self.draw_panel_scrollbar(
            screen,
            self.items_panel,
            self.item_scroll,
            len(self.state.inventory),
            self.ITEM_VISIBLE_ROWS,
        )

    def draw_item_row(self, screen, item, y):
        row_rect = self.item_row_rect(y)
        is_selected = item is self.selected_item
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

        line_1 = truncate_text(f"{item.name} [{item.rarity} {item.slot}]", self.font, 420)
        line_2 = truncate_text(f"Value {item.value}g", self.small_font, 420)

        screen.blit(self.font.render(line_1, True, (230, 230, 240)), (row_rect.x + 12, row_rect.y + 8))
        screen.blit(self.small_font.render(line_2, True, (180, 180, 195)), (row_rect.x + 12, row_rect.y + 29))

    def draw_heroes(self, screen):
        visible = self.visible_heroes()

        if not visible:
            screen.blit(
                self.font.render("No heroes hired yet.", True, (180, 180, 190)),
                (584, self.hero_row_start_y + 8),
            )
            self.draw_panel_scrollbar(
                screen,
                self.heroes_panel,
                self.hero_scroll,
                len(self.state.roster),
                self.HERO_VISIBLE_ROWS,
            )
            return

        y = self.hero_row_start_y
        for hero in visible:
            self.draw_hero_row(screen, hero, y)
            y += self.HERO_ROW_SPACING

        self.draw_panel_scrollbar(
            screen,
            self.heroes_panel,
            self.hero_scroll,
            len(self.state.roster),
            self.HERO_VISIBLE_ROWS,
        )

    def draw_hero_row(self, screen, hero, y):
        row_rect = self.hero_row_rect(y)
        is_selected = hero is self.selected_hero
        is_hovered = row_rect.collidepoint(self.mouse_pos)

        if is_selected:
            fill_color = (52, 70, 56)
            border_color = (150, 220, 160)
            border_width = 2
        elif is_hovered:
            fill_color = (48, 64, 52)
            border_color = (100, 150, 110)
            border_width = 1
        else:
            fill_color = (42, 54, 44)
            border_color = (72, 96, 76)
            border_width = 1

        pygame.draw.rect(screen, fill_color, row_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, row_rect, border_width, border_radius=8)

        equipped = self.equipment_summary(hero)
        line_1 = truncate_text(
            f"{hero.name} | {hero.hero_class} | Lv {hero.level} | Pwr {hero.combat_power()}",
            self.font,
            600,
        )
        line_2 = truncate_text(f"Equipment: {equipped}", self.small_font, 600)

        screen.blit(self.font.render(line_1, True, (210, 240, 210)), (row_rect.x + 12, row_rect.y + 8))
        screen.blit(self.small_font.render(line_2, True, (180, 210, 180)), (row_rect.x + 12, row_rect.y + 29))

    def draw_equipment(self, screen):
        equipment_rows = self.selected_hero_equipment_rows()

        if self.selected_hero is None:
            screen.blit(
                self.small_font.render("Select a hero to view equipped items.", True, (180, 180, 190)),
                (584, self.equipment_row_start_y + 4),
            )
            return

        if not equipment_rows:
            screen.blit(
                self.small_font.render(f"{self.selected_hero.name} has no equipped items.", True, (180, 180, 190)),
                (584, self.equipment_row_start_y + 4),
            )
            return

        visible_rows = self.visible_equipment_rows()

        y = self.equipment_row_start_y
        for slot, item in visible_rows:
            self.draw_equipment_row(screen, slot, item, y)
            y += self.EQUIPMENT_ROW_SPACING

    def draw_equipment_row(self, screen, slot, item, y):
        row_rect = self.equipment_row_rect(y)
        is_selected = slot == self.selected_equipment_slot
        is_hovered = row_rect.collidepoint(self.mouse_pos)

        if is_selected:
            fill_color = (70, 58, 48)
            border_color = (220, 170, 100)
            border_width = 2
        elif is_hovered:
            fill_color = (60, 52, 44)
            border_color = (150, 120, 85)
            border_width = 1
        else:
            fill_color = (48, 42, 38)
            border_color = (88, 76, 66)
            border_width = 1

        pygame.draw.rect(screen, fill_color, row_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, row_rect, border_width, border_radius=8)

        line = truncate_text(f"{slot}: {item.name} [{item.rarity}]", self.small_font, 610)
        screen.blit(self.small_font.render(line, True, (230, 220, 200)), (row_rect.x + 10, row_rect.y + 8))

    def draw_details(self, screen):
        left_x = 44
        right_x = 640

        detail_item = self.selected_item
        if detail_item is None and self.selected_hero and self.selected_equipment_slot:
            detail_item = self.selected_hero.equipment.get(self.selected_equipment_slot)

        if detail_item:
            item_lines = self.item_detail_lines(detail_item)
        else:
            item_lines = ["Item: None selected"]

        if self.selected_hero:
            hero_lines = self.hero_detail_lines(self.selected_hero)
        else:
            hero_lines = ["Hero: None selected"]

        y = 562

        if item_lines:
            for line in item_lines[:2]:
                screen.blit(self.small_font.render(line, True, (210, 210, 220)), (left_x, y))
                y += 20

            if len(item_lines) > 2:
                for wrapped_line in wrap_text(item_lines[2], self.small_font, 540)[:4]:
                    screen.blit(self.small_font.render(wrapped_line, True, (210, 210, 220)), (left_x, y))
                    y += 20

            if len(item_lines) > 3:
                screen.blit(self.small_font.render(item_lines[3], True, (210, 210, 220)), (left_x, y))

        y = 562
        for line in hero_lines[:6]:
            screen.blit(self.small_font.render(line, True, (210, 210, 220)), (right_x, y))
            y += 20

    def build_buttons(self):
        buttons = [
            Button((1120, 40, 80, 32), "Hub", self.on_return_to_hub),
        ]

        action_button_rect = (1010, 642, 190, 42)

        if self.selected_item and self.selected_hero:
            buttons.append(Button(action_button_rect, "Equip Item", self.equip_selected_item))
        elif self.selected_hero and self.selected_equipment_slot:
            buttons.append(Button(action_button_rect, "Unequip Item", self.unequip_selected_item))

        return buttons

    def handle_row_click(self, pos):
        y = self.item_row_start_y
        for item in self.visible_items():
            if self.item_row_rect(y).collidepoint(pos):
                self.selected_item = item
                self.selected_equipment_slot = None
                self.status_message = f"Selected item: {item.name}"
                return
            y += self.ITEM_ROW_SPACING

        y = self.hero_row_start_y
        for hero in self.visible_heroes():
            if self.hero_row_rect(y).collidepoint(pos):
                self.selected_hero = hero
                self.selected_equipment_slot = None
                self.equipment_scroll = 0
                self.status_message = f"Selected hero: {hero.name}"
                return
            y += self.HERO_ROW_SPACING

        y = self.equipment_row_start_y
        for slot, item in self.visible_equipment_rows():
            if self.equipment_row_rect(y).collidepoint(pos):
                self.selected_equipment_slot = slot
                self.selected_item = None
                self.status_message = f"Selected equipped item: {item.name}"
                return
            y += self.EQUIPMENT_ROW_SPACING

    def equip_selected_item(self):
        if not self.selected_item or not self.selected_hero:
            self.status_message = "Select both an item and a hero."
            return

        item = self.selected_item
        hero = self.selected_hero

        if not item.can_equip(hero.hero_class):
            self.status_message = f"{hero.name} cannot equip {item.name}."
            return

        if item not in self.state.inventory:
            self.status_message = "That item is no longer in inventory."
            self.selected_item = None
            return

        replaced_item = hero.equipment.get(item.slot)

        self.state.inventory.remove(item)

        if replaced_item:
            self.state.inventory.append(replaced_item)

        hero.equipment[item.slot] = item

        self.selected_item = None
        self.selected_equipment_slot = item.slot

        self.item_scroll = clamp_scroll(
            self.item_scroll,
            len(self.state.inventory),
            self.ITEM_VISIBLE_ROWS,
        )

        self.equipment_scroll = clamp_scroll(
            self.equipment_scroll,
            len(self.selected_hero_equipment_rows()),
            self.EQUIPMENT_VISIBLE_ROWS,
        )

        if self.on_save_game:
            self.on_save_game()

        if replaced_item:
            self.status_message = f"Equipped {item.name}; moved {replaced_item.name} to inventory."
        else:
            self.status_message = f"Equipped {item.name} to {hero.name}."

    def unequip_selected_item(self):
        if not self.selected_hero or not self.selected_equipment_slot:
            self.status_message = "Select an equipped item to unequip."
            return

        hero = self.selected_hero
        slot = self.selected_equipment_slot

        if slot not in hero.equipment:
            self.status_message = "That equipment slot is already empty."
            self.selected_equipment_slot = None
            return

        item = hero.equipment.pop(slot)
        self.state.inventory.append(item)

        self.selected_item = item
        self.selected_equipment_slot = None

        self.item_scroll = clamp_scroll(
            self.item_scroll,
            len(self.state.inventory),
            self.ITEM_VISIBLE_ROWS,
        )

        self.equipment_scroll = clamp_scroll(
            self.equipment_scroll,
            len(self.selected_hero_equipment_rows()),
            self.EQUIPMENT_VISIBLE_ROWS,
        )

        if self.on_save_game:
            self.on_save_game()

        self.status_message = f"Unequipped {item.name} from {hero.name}."

    def visible_items(self):
        end = self.item_scroll + self.ITEM_VISIBLE_ROWS
        return self.state.inventory[self.item_scroll:end]

    def visible_heroes(self):
        end = self.hero_scroll + self.HERO_VISIBLE_ROWS
        return self.state.roster[self.hero_scroll:end]

    def selected_hero_equipment_rows(self):
        if self.selected_hero is None:
            return []

        return list(self.selected_hero.equipment.items())

    def visible_equipment_rows(self):
        equipment_rows = self.selected_hero_equipment_rows()
        end = self.equipment_scroll + self.EQUIPMENT_VISIBLE_ROWS
        return equipment_rows[self.equipment_scroll:end]

    def equipment_summary(self, hero):
        if not hero.equipment:
            return "None"

        parts = []
        for slot, item in hero.equipment.items():
            parts.append(f"{slot}: {item.name}")

        return ", ".join(parts)

    def item_detail_lines(self, item):
        lines = [
            f"Item: {item.name}",
            f"Slot: {item.slot}    Rarity: {item.rarity}    Value: {item.value}g",
        ]

        bonus_parts = []
        for stat, value in item.stat_bonuses.items():
            bonus_parts.append(f"+{value} {stat}")

        for damage, value in item.damage_type_bonus.items():
            bonus_parts.append(f"+{int(value * 100)}% {damage} damage")

        for enemy, value in item.enemy_type_bonus.items():
            bonus_parts.append(f"+{int(value * 100)}% vs {enemy}")

        for enemy, value in item.enemy_type_resistance.items():
            bonus_parts.append(f"-{int(value * 100)}% damage from {enemy}")

        detail = "; ".join(bonus_parts) if bonus_parts else "No bonuses"
        classes = ", ".join(item.class_restrictions) if item.class_restrictions else "Any"

        lines.append(f"Bonuses: {detail}")
        lines.append(f"Classes: {classes}")

        return lines

    def hero_detail_lines(self, hero):
        lines = [
            f"Hero: {hero.name}",
            f"Class: {hero.hero_class}    Level: {hero.level}    Power: {hero.combat_power()}",
            (
                f"Stats: Might {hero.total_stat('might')}    "
                f"Agility {hero.total_stat('agility')}    "
                f"Mind {hero.total_stat('mind')}    "
                f"Spirit {hero.total_stat('spirit')}"
            ),
            truncate_text(f"Equipment: {self.equipment_summary(hero)}", self.small_font, 560),
        ]

        return lines

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

    def item_row_rect(self, y):
        return pygame.Rect(34, y - 8, 480, 44)

    def hero_row_rect(self, y):
        return pygame.Rect(584, y - 8, 640, 44)

    def equipment_row_rect(self, y):
        return pygame.Rect(584, y - 4, 640, 28)