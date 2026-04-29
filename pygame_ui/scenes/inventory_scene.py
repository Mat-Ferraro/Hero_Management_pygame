from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.ui_helpers import truncate_text
from pygame_ui.widgets.details_panel import DetailsPanel
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.row_styles import draw_selectable_row
from pygame_ui.widgets.scrollable_list_panel import ScrollableListPanel

from ..widgets.button import Button


class InventoryScene(SceneBase):
    def __init__(self, state, on_return_to_hub, on_save_game):
        super().__init__()

        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        self.status_message = "Select an item and a hero."

        self.selected_item = None
        self.selected_hero = None
        self.selected_equipment_slot = None

        self.details_panel = DetailsPanel((20, 520, 1240, 185), "Selection Details")

        self.items_panel = ScrollableListPanel(
            rect=(20, 120, 520, 380),
            title="Items",
            row_height=44,
            row_spacing=52,
            visible_rows=5,
            font=self.font,
            title_font=self.title_font,
            padding=14,
            title_height=60,
        )

        self.heroes_panel = ScrollableListPanel(
            rect=(560, 120, 700, 270),
            title="Heroes",
            row_height=44,
            row_spacing=52,
            visible_rows=5,
            font=self.font,
            title_font=self.title_font,
            padding=24,
            title_height=60,
        )

        self.equipment_panel = ScrollableListPanel(
            rect=(560, 410, 700, 90),
            title="Selected Hero Equipment",
            row_height=28,
            row_spacing=34,
            visible_rows=3,
            font=self.small_font,
            title_font=self.title_font,
            padding=24,
            title_height=38,
        )

    def sync_lists(self):
        self.items_panel.set_items(self.state.inventory)
        self.heroes_panel.set_items(self.state.roster)
        self.equipment_panel.set_items(self.selected_hero_equipment_rows())

    def handle_event(self, event):
        self.sync_lists()

        if self.items_panel.handle_event(event):
            return

        if self.heroes_panel.handle_event(event):
            return

        if self.equipment_panel.handle_event(event):
            return

        if self.handle_buttons_click(event, self.build_buttons()):
            return

        if self.is_left_click(event):
            self.handle_row_click(event.pos)

    def update(self, mouse_pos):
        super().update(mouse_pos)
        self.sync_lists()

        self.items_panel.update(mouse_pos)
        self.heroes_panel.update(mouse_pos)
        self.equipment_panel.update(mouse_pos)

    def draw(self, screen):
        self.sync_lists()
        self.clear_screen(screen)

        self.draw_header(screen)

        self.items_panel.draw(
            screen=screen,
            row_drawer=self.draw_item_row,
            selected_item=self.selected_item,
            empty_text="No items in inventory.",
        )

        self.heroes_panel.draw(
            screen=screen,
            row_drawer=self.draw_hero_row,
            selected_item=self.selected_hero,
            empty_text="No heroes hired yet.",
        )

        self.equipment_panel.draw(
            screen=screen,
            row_drawer=self.draw_equipment_row,
            selected_item=self.selected_equipment_row(),
            empty_text=self.equipment_empty_text(),
        )

        self.draw_details(screen)
        self.update_and_draw_buttons(screen, self.build_buttons())

    def draw_header(self, screen):
        stats = (
            f"Gold: {self.state.gold}g    "
            f"Roster: {len(self.state.roster)}/{self.state.guild_upgrades.roster_capacity}    "
            f"Inventory: {len(self.state.inventory)}"
        )

        HeaderPanel(
            title="Inventory",
            stats=stats,
            status_message=self.status_message,
        ).draw(screen, self.title_font, self.header_font, self.font)

    def draw_item_row(self, screen, item, row_rect, is_selected, is_hovered):
        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style="dark",
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

        screen.blit(self.font.render(line_1, True, theme.TEXT_PRIMARY), (row_rect.x + 12, row_rect.y + 8))
        screen.blit(self.small_font.render(line_2, True, theme.TEXT_MUTED), (row_rect.x + 12, row_rect.y + 29))

    def draw_hero_row(self, screen, hero, row_rect, is_selected, is_hovered):
        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style="green",
        )

        subclass = hero.subclass or "No Subclass"

        line_1 = truncate_text(
            f"{hero.name} | {hero.hero_class}/{subclass} | Lv {hero.level} | Pwr {hero.combat_power()}",
            self.font,
            row_rect.width - 24,
        )
        line_2 = truncate_text(
            f"Age {hero.age} ({hero.career_stage()}) | Ability: {hero.special_ability or 'None'} | Mentor {hero.mentorship_value()}",
            self.small_font,
            row_rect.width - 24,
        )

        screen.blit(self.font.render(line_1, True, (210, 240, 210)), (row_rect.x + 12, row_rect.y + 8))
        screen.blit(self.small_font.render(line_2, True, (180, 210, 180)), (row_rect.x + 12, row_rect.y + 29))

    def draw_equipment_row(self, screen, row, row_rect, is_selected, is_hovered):
        slot, item = row

        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style="brown",
        )

        line = truncate_text(
            f"{slot}: {item.name} [{item.rarity}]",
            self.small_font,
            row_rect.width - 20,
        )

        screen.blit(self.small_font.render(line, True, (230, 220, 200)), (row_rect.x + 10, row_rect.y + 8))

    def draw_details(self, screen):
        detail_item = self.selected_item
        if detail_item is None and self.selected_hero and self.selected_equipment_slot:
            detail_item = self.selected_hero.equipment.get(self.selected_equipment_slot)

        item_lines = self.item_detail_lines(detail_item) if detail_item else ["Item: None selected"]
        hero_lines = self.hero_detail_lines(self.selected_hero) if self.selected_hero else ["Hero: None selected"]

        self.details_panel.draw_two_columns(
            screen=screen,
            title_font=self.title_font,
            font=self.small_font,
            left_lines=item_lines,
            right_lines=hero_lines,
            left_width=540,
            right_width=560,
        )

    def build_buttons(self):
        buttons = [
            Button(theme.HUB_BUTTON_RECT, "Hub", self.on_return_to_hub),
        ]

        if self.selected_item and self.selected_hero:
            buttons.append(Button(theme.DETAIL_ACTION_BUTTON_RECT, "Equip Item", self.equip_selected_item))
        elif self.selected_hero and self.selected_equipment_slot:
            buttons.append(Button(theme.DETAIL_ACTION_BUTTON_RECT, "Unequip Item", self.unequip_selected_item))

        return buttons

    def handle_row_click(self, pos):
        item = self.items_panel.item_at_pos(pos)
        if item is not None:
            self.selected_item = item
            self.selected_equipment_slot = None
            self.status_message = f"Selected item: {item.name}"
            return

        hero = self.heroes_panel.item_at_pos(pos)
        if hero is not None:
            self.selected_hero = hero
            self.selected_equipment_slot = None
            self.status_message = f"Selected hero: {hero.name}"
            self.sync_lists()
            return

        equipment_row = self.equipment_panel.item_at_pos(pos)
        if equipment_row is not None:
            slot, item = equipment_row
            self.selected_equipment_slot = slot
            self.selected_item = None
            self.status_message = f"Selected equipped item: {item.name}"

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
        self.sync_lists()

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
        self.sync_lists()

        if self.on_save_game:
            self.on_save_game()

        self.status_message = f"Unequipped {item.name} from {hero.name}."

    def selected_hero_equipment_rows(self):
        if self.selected_hero is None:
            return []

        return list(self.selected_hero.equipment.items())

    def selected_equipment_row(self):
        if self.selected_hero is None or self.selected_equipment_slot is None:
            return None

        for row in self.selected_hero_equipment_rows():
            if row[0] == self.selected_equipment_slot:
                return row

        return None

    def equipment_empty_text(self):
        if self.selected_hero is None:
            return "Select a hero to view equipped items."

        return f"{self.selected_hero.name} has no equipped items."

    def equipment_summary(self, hero):
        if not hero.equipment:
            return "None"

        return ", ".join(f"{slot}: {item.name}" for slot, item in hero.equipment.items())

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
        return [
            f"Hero: {hero.name}",
            f"Class: {hero.hero_class}    Subclass: {hero.subclass or 'None'}",
            f"Ability: {hero.special_ability or 'None'}",
            f"Age: {hero.age}    Stage: {hero.career_stage()}    Age Power: x{hero.age_power_multiplier():.2f}",
            f"Level: {hero.level}    Power: {hero.combat_power()}    Mentor: {hero.mentorship_value()}",
            f"Stats: Might {hero.total_stat('might')}    Agility {hero.total_stat('agility')}    Mind {hero.total_stat('mind')}    Spirit {hero.total_stat('spirit')}",
            truncate_text(f"Equipment: {self.equipment_summary(hero)}", self.small_font, 560),
        ]