from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.ui_helpers import truncate_text
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.key_value_grid import KeyValueGrid
from pygame_ui.widgets.navigation_buttons import action_button, hub_button
from pygame_ui.widgets.resource_header import ResourceHeader
from pygame_ui.widgets.selection_details_panel import SelectionDetailsPanel
from pygame_ui.widgets.status_chip import StatusChip
from pygame_ui.widgets.text_block import TextBlock
from pygame_ui.widgets.row_styles import draw_selectable_row
from pygame_ui.widgets.scrollable_list_panel import ScrollableListPanel


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

        self.details_panel = SelectionDetailsPanel(
            rect=(40, 790, 1840, 230),
            title="Selection Details",
            empty_message="Select an item or hero to inspect.",
            left_width=520,
            right_width=1120,
        )

        self.items_panel = ScrollableListPanel(
            rect=(40, 150, 680, 600),
            title="Items",
            row_height=70,
            row_gap=10,
            visible_rows=None,
            font=self.font,
            title_font=self.title_font,
            padding=18,
            title_height=64,
        )

        self.heroes_panel = ScrollableListPanel(
            rect=(760, 150, 1120, 390),
            title="Heroes",
            row_height=70,
            row_gap=10,
            visible_rows=None,
            font=self.font,
            title_font=self.title_font,
            padding=18,
            title_height=64,
        )

        self.equipment_panel = ScrollableListPanel(
            rect=(760, 570, 1120, 180),
            title="Selected Hero Equipment",
            row_height=40,
            row_gap=8,
            visible_rows=None,
            font=self.small_font,
            title_font=self.title_font,
            padding=18,
            title_height=52,
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
        HeaderPanel(
            rect=(40, 30, 1840, 96),
            title="Inventory",
            stats="",
            status_message=self.status_message,
            stats_pos=(70, 70),
            status_pos=(1080, 108),
        ).draw(screen, self.title_font, self.header_font, self.font)

        ResourceHeader(
            resources=[
                ("Gold", f"{self.state.gold}g"),
                ("Roster", f"{len(self.state.roster)}/{self.state.guild_upgrades.roster_capacity}"),
                ("Items", len(self.state.inventory)),
                ("Equipped", self.total_equipped_items()),
            ],
            spacing=210,
            item_max_width=180,
            font_size=24,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=False,
            value_bold=True,
        ).draw(screen, self.font, 60, 72)

    def draw_item_row(self, screen, item, row_rect, is_selected, is_hovered):
        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style="dark",
        )

        screen.blit(
            self.font.render(
                truncate_text(f"{item.name} [{item.rarity}]", self.font, row_rect.width - 130),
                True,
                theme.TEXT_PRIMARY,
            ),
            (row_rect.x + 14, row_rect.y + 10),
        )

        StatusChip(
            rect=(row_rect.right - 106, row_rect.y + 10, 90, 26),
            text=f"{item.value}g",
            style="warning" if item.value >= 250 else "good",
        ).draw(screen, self.small_font)

        StatusChip(
            rect=(row_rect.x + 14, row_rect.y + 42, 92, 24),
            text=item.slot,
            style="info",
        ).draw(screen, self.small_font)

        TextBlock(
            lines=[self.item_bonus_summary(item)],
            color=theme.TEXT_MUTED,
            row_spacing=18,
            max_lines=1,
        ).draw(
            screen=screen,
            font=self.small_font,
            x=row_rect.x + 118,
            y=row_rect.y + 45,
            max_width=row_rect.width - 140,
        )

    def draw_hero_row(self, screen, hero, row_rect, is_selected, is_hovered):
        can_equip_selected_item = True
        if self.selected_item is not None:
            can_equip_selected_item = self.selected_item.can_equip(hero.hero_class)

        row_style = "green" if can_equip_selected_item else "dark"

        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style=row_style,
        )

        subclass = hero.subclass or "No Subclass"
        health_style = self.health_chip_style(hero)

        name_color = (210, 240, 210) if can_equip_selected_item else theme.TEXT_MUTED
        detail_color = (180, 210, 180) if can_equip_selected_item else (145, 145, 155)

        screen.blit(
            self.font.render(
                truncate_text(
                    f"{hero.name} | {hero.hero_class}/{subclass} | Lv {hero.level}",
                    self.font,
                    row_rect.width - 250,
                ),
                True,
                name_color,
            ),
            (row_rect.x + 14, row_rect.y + 10),
        )

        eligibility_text = "Eligible" if can_equip_selected_item else "Cannot Equip"
        eligibility_style = "good" if can_equip_selected_item else "danger"

        StatusChip(
            rect=(row_rect.right - 220, row_rect.y + 10, 102, 26),
            text=eligibility_text if self.selected_item is not None else hero.health_status(),
            style=eligibility_style if self.selected_item is not None else health_style,
        ).draw(screen, self.small_font)

        StatusChip(
            rect=(row_rect.right - 108, row_rect.y + 10, 92, 26),
            text=f"Pwr {hero.combat_power()}",
            style="info",
        ).draw(screen, self.small_font)

        TextBlock(
            lines=[
                f"Age {hero.age} ({hero.career_stage()}) | Ability: {hero.special_ability or 'None'} | Mentor {hero.mentorship_value()} | Equipped {len(hero.equipment)}"
            ],
            color=detail_color,
            row_spacing=18,
            max_lines=1,
        ).draw(
            screen=screen,
            font=self.small_font,
            x=row_rect.x + 14,
            y=row_rect.y + 45,
            max_width=row_rect.width - 28,
        )

    def draw_equipment_row(self, screen, row, row_rect, is_selected, is_hovered):
        slot, item = row

        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style="brown",
        )

        StatusChip(
            rect=(row_rect.x + 10, row_rect.y + 8, 92, 24),
            text=slot,
            style="info",
        ).draw(screen, self.small_font)

        screen.blit(
            self.small_font.render(
                truncate_text(f"{item.name} [{item.rarity}]", self.small_font, row_rect.width - 124),
                True,
                (230, 220, 200),
            ),
            (row_rect.x + 116, row_rect.y + 12),
        )

    def draw_details(self, screen):
        detail_item = self.selected_item
        if detail_item is None and self.selected_hero and self.selected_equipment_slot:
            detail_item = self.selected_hero.equipment.get(self.selected_equipment_slot)

        if detail_item is None and self.selected_hero is None:
            self.details_panel.draw(
                screen=screen,
                title_font=self.title_font,
                font=self.font,
                left_lines=[],
                right_lines=[],
            )
            return

        if detail_item is None:
            left_lines = ["Item: None selected"]
        else:
            left_lines = []

        if self.selected_hero is None:
            right_lines = ["Hero: None selected"]
        else:
            right_lines = []

        self.details_panel.details_panel.panel.draw(screen, self.title_font)

        left_x = self.details_panel.rect.x + 28
        right_x = self.details_panel.rect.x + 640
        top_y = self.details_panel.rect.y + 52

        if detail_item is not None:
            KeyValueGrid(
                rows=[
                    ("Item", detail_item.name),
                    ("Slot", detail_item.slot),
                    ("Rarity", detail_item.rarity),
                    ("Value", f"{detail_item.value}g"),
                    ("Classes", ", ".join(detail_item.class_restrictions) if detail_item.class_restrictions else "Any"),
                    ("Bonuses", self.item_bonus_summary(detail_item)),
                ],
                columns=1,
                column_width=520,
                row_gap=10,
                label_color=theme.TEXT_MUTED,
                value_color=theme.TEXT_PRIMARY,
                label_bold=True,
                value_bold=False,
                font_size=22,
                line_spacing=2,
            ).draw(
                screen=screen,
                font=self.font,
                x=left_x,
                y=top_y,
            )
        else:
            TextBlock(
                lines=left_lines,
                color=theme.TEXT_SECONDARY,
                row_spacing=24,
            ).draw(screen, self.font, left_x, top_y, 520)

        if self.selected_hero is not None:
            hero = self.selected_hero
            KeyValueGrid(
                rows=[
                    ("Hero", hero.name),
                    ("Class", f"{hero.hero_class}"),
                    ("Subclass", hero.subclass or "None"),
                    ("Ability", hero.special_ability or "None"),
                    ("Age", f"{hero.age} ({hero.career_stage()})"),
                    ("Age Power", f"x{hero.age_power_multiplier():.2f}"),
                    ("Level", hero.level),
                    ("Power", hero.combat_power()),
                    ("Mentor", hero.mentorship_value()),
                    ("Stats", f"Might {hero.total_stat('might')} | Agility {hero.total_stat('agility')} | Mind {hero.total_stat('mind')} | Spirit {hero.total_stat('spirit')}"),
                    ("Equipment", self.equipment_summary(hero)),
                ],
                columns=1,
                column_width=1040,
                row_gap=10,
                label_color=theme.TEXT_MUTED,
                value_color=theme.TEXT_PRIMARY,
                label_bold=True,
                value_bold=False,
                font_size=22,
                line_spacing=2,
            ).draw(
                screen=screen,
                font=self.font,
                x=right_x,
                y=top_y,
            )
        else:
            TextBlock(
                lines=right_lines,
                color=theme.TEXT_SECONDARY,
                row_spacing=24,
            ).draw(screen, self.font, right_x, top_y, 1040)

    def build_buttons(self):
        buttons = [
            hub_button(self.on_return_to_hub),
        ]

        if self.selected_item and self.selected_hero:
            buttons.append(action_button("Equip Item", self.equip_selected_item, rect=(1660, 956, 180, 44)))
        elif self.selected_hero and self.selected_equipment_slot:
            buttons.append(action_button("Unequip Item", self.unequip_selected_item, rect=(1660, 956, 180, 44)))

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

    def total_equipped_items(self):
        return sum(len(hero.equipment) for hero in self.state.roster)

    def equipment_summary(self, hero):
        if not hero.equipment:
            return "None"
        return ", ".join(f"{slot}: {item.name}" for slot, item in hero.equipment.items())

    def health_chip_style(self, hero):
        if hero.health_status() in ("DEAD", "CRITICAL"):
            return "danger"
        if hero.health_status() in ("WOUNDED", "HURT") or hero.injured_years_remaining > 0:
            return "warning"
        return "good"

    def item_bonus_summary(self, item):
        if item is None:
            return "No item selected"

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