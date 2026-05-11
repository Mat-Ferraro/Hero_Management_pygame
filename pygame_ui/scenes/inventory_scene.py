"""
pygame_ui/scenes/inventory_scene.py

Inventory and equipment management scene.

Changes from previous version:
  - Equip/unequip routed through systems.equipment.equipment_rules
    (enforces category slots, capacity limits, class restrictions).
  - Hero rows show capacity (used/total slots) and synergy indicator.
  - Details panel shows tags, drawbacks, capacity cost, and active synergies.
  - Item rows show category label instead of old free-string slot.
  - Consumables flagged visually; equip button hidden for them.
"""

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
from systems.equipment.equipment_rules import (
    can_equip,
    capacity_display,
    equip_item,
    loadout_summary,
    unequip_item,
)
from systems.equipment.equipment_synergies import (
    has_any_active_synergy,
    synergy_summary_lines,
)


class InventoryScene(SceneBase):
    def __init__(self, state, on_return_to_hub, on_save_game):
        super().__init__()

        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        self.status_message = "Select an item and a hero."
        self.selected_item = None
        self.selected_hero = None
        self.selected_equipment_category = None

        self.details_panel = SelectionDetailsPanel(
            rect=(40, 790, 1840, 230),
            title="Selection Details",
            empty_message="Select an item or hero to inspect.",
            left_width=520,
            right_width=1120,
        )
        self.items_panel = ScrollableListPanel(
            rect=(40, 150, 680, 600), title="Guild Inventory",
            row_height=70, row_gap=10, visible_rows=None,
            font=self.font, title_font=self.title_font, padding=18, title_height=64,
        )
        self.heroes_panel = ScrollableListPanel(
            rect=(760, 150, 1120, 390), title="Heroes",
            row_height=70, row_gap=10, visible_rows=None,
            font=self.font, title_font=self.title_font, padding=18, title_height=64,
        )
        self.equipment_panel = ScrollableListPanel(
            rect=(760, 570, 1120, 180), title="Selected Hero Loadout",
            row_height=40, row_gap=8, visible_rows=None,
            font=self.small_font, title_font=self.title_font, padding=18, title_height=52,
        )

    def sync_lists(self):
        self.items_panel.set_items(self.state.inventory)
        self.heroes_panel.set_items(self.state.roster)
        self.equipment_panel.set_items(self._hero_equipment_rows())

    def handle_event(self, event):
        self.sync_lists()
        if self.items_panel.handle_event(event): return
        if self.heroes_panel.handle_event(event): return
        if self.equipment_panel.handle_event(event): return
        if self.handle_buttons_click(event, self.build_buttons()): return
        if self.is_left_click(event): self._handle_row_click(event.pos)

    def update(self, mouse_pos):
        super().update(mouse_pos)
        self.sync_lists()
        self.items_panel.update(mouse_pos)
        self.heroes_panel.update(mouse_pos)
        self.equipment_panel.update(mouse_pos)

    def draw(self, screen):
        self.sync_lists()
        self.clear_screen(screen)
        self._draw_header(screen)
        self.items_panel.draw(screen=screen, row_drawer=self._draw_item_row,
                              selected_item=self.selected_item, empty_text="No items in guild inventory.")
        self.heroes_panel.draw(screen=screen, row_drawer=self._draw_hero_row,
                               selected_item=self.selected_hero, empty_text="No heroes hired yet.")
        self.equipment_panel.draw(screen=screen, row_drawer=self._draw_equipment_row,
                                  selected_item=self._selected_equipment_row(),
                                  empty_text=self._equipment_empty_text())
        self._draw_details(screen)
        self.update_and_draw_buttons(screen, self.build_buttons())

    def _draw_header(self, screen):
        HeaderPanel(
            rect=(40, 30, 1840, 96), title="Inventory", stats="",
            status_message=self.status_message, stats_pos=(70, 70), status_pos=(1080, 108),
        ).draw(screen, self.title_font, self.header_font, self.font)
        ResourceHeader(
            resources=[
                ("Gold",      f"{self.state.gold}g"),
                ("Roster",    f"{len(self.state.roster)}/{self.state.guild_upgrades.roster_capacity}"),
                ("Inventory", len(self.state.inventory)),
                ("Equipped",  self._total_equipped()),
            ],
            spacing=210, item_max_width=180, font_size=24,
            label_color=theme.TEXT_MUTED, value_color=theme.TEXT_PRIMARY,
            label_bold=False, value_bold=True,
        ).draw(screen, self.font, 60, 72)

    def _draw_item_row(self, screen, item, row_rect, is_selected, is_hovered):
        draw_selectable_row(screen=screen, rect=row_rect, is_selected=is_selected,
                            is_hovered=is_hovered, style="dark")
        screen.blit(
            self.font.render(
                truncate_text(f"{item.name} [{item.rarity}]", self.font, row_rect.width - 130),
                True, theme.TEXT_PRIMARY,
            ), (row_rect.x + 14, row_rect.y + 10),
        )
        StatusChip(rect=(row_rect.right - 106, row_rect.y + 10, 90, 26),
                   text=f"{item.value}g",
                   style="warning" if item.value >= 250 else "good").draw(screen, self.small_font)
        cat_label = "CONSUMABLE" if item.consumable else item.category
        cat_style = "danger" if item.consumable else "info"
        StatusChip(rect=(row_rect.x + 14, row_rect.y + 42, 110, 24),
                   text=cat_label, style=cat_style).draw(screen, self.small_font)
        TextBlock(lines=[self._item_bonus_summary(item)], color=theme.TEXT_MUTED,
                  row_spacing=18, max_lines=1).draw(
            screen=screen, font=self.small_font,
            x=row_rect.x + 136, y=row_rect.y + 45, max_width=row_rect.width - 158)

    def _draw_hero_row(self, screen, hero, row_rect, is_selected, is_hovered):
        can_eq = True
        if self.selected_item is not None and not self.selected_item.consumable:
            ok, _ = can_equip(hero, self.selected_item)
            can_eq = ok

        draw_selectable_row(screen=screen, rect=row_rect, is_selected=is_selected,
                            is_hovered=is_hovered, style="green" if can_eq else "dark")

        name_color   = (210, 240, 210) if can_eq else theme.TEXT_MUTED
        detail_color = (180, 210, 180) if can_eq else (145, 145, 155)
        subclass = hero.subclass or "No Subclass"

        screen.blit(
            self.font.render(
                truncate_text(f"{hero.name} | {hero.hero_class}/{subclass} | Lv {hero.level}",
                              self.font, row_rect.width - 250),
                True, name_color,
            ), (row_rect.x + 14, row_rect.y + 10),
        )

        if self.selected_item and not self.selected_item.consumable:
            elig_text  = "Eligible" if can_eq else "Cannot Equip"
            elig_style = "good" if can_eq else "danger"
        else:
            elig_text  = hero.health_status()
            elig_style = self._health_chip_style(hero)

        StatusChip(rect=(row_rect.right - 220, row_rect.y + 10, 102, 26),
                   text=elig_text, style=elig_style).draw(screen, self.small_font)
        StatusChip(rect=(row_rect.right - 108, row_rect.y + 10, 92, 26),
                   text=f"Pwr {hero.combat_power()}", style="info").draw(screen, self.small_font)

        cap = capacity_display(hero)
        syn = " | ✦ Synergy" if has_any_active_synergy(hero) else ""
        TextBlock(lines=[f"Age {hero.age} | {cap} | Equipped {len(hero.equipment)}{syn}"],
                  color=detail_color, row_spacing=18, max_lines=1).draw(
            screen=screen, font=self.small_font,
            x=row_rect.x + 14, y=row_rect.y + 45, max_width=row_rect.width - 28)

    def _draw_equipment_row(self, screen, row, row_rect, is_selected, is_hovered):
        category, item = row
        draw_selectable_row(screen=screen, rect=row_rect, is_selected=is_selected,
                            is_hovered=is_hovered, style="brown")
        StatusChip(rect=(row_rect.x + 10, row_rect.y + 8, 92, 24),
                   text=category, style="info").draw(screen, self.small_font)
        screen.blit(
            self.small_font.render(
                truncate_text(f"{item.name} [{item.rarity}]", self.small_font, row_rect.width - 124),
                True, (230, 220, 200),
            ), (row_rect.x + 116, row_rect.y + 12),
        )

    def _draw_details(self, screen):
        detail_item = self.selected_item
        if detail_item is None and self.selected_hero and self.selected_equipment_category:
            detail_item = self.selected_hero.equipment.get(self.selected_equipment_category)

        self.details_panel.details_panel.panel.draw(screen, self.title_font)
        left_x  = self.details_panel.rect.x + 28
        right_x = self.details_panel.rect.x + 640
        top_y   = self.details_panel.rect.y + 52

        if detail_item is not None:
            rows = [
                ("Item",     detail_item.name),
                ("Category", detail_item.category),
                ("Rarity",   detail_item.rarity),
                ("Value",    f"{detail_item.value}g"),
                ("Classes",  ", ".join(detail_item.class_restrictions) if detail_item.class_restrictions else "Any"),
                ("Tags",     detail_item.tag_list_display()),
                ("Bonuses",  self._item_bonus_summary(detail_item)),
            ]
            if detail_item.drawbacks:
                rows.append(("Drawback", "; ".join(detail_item.drawbacks)))
            if detail_item.consumable:
                rows.append(("Type", "CONSUMABLE — single use"))
            if detail_item.equip_capacity_cost > 1:
                rows.append(("Slot cost", f"{detail_item.equip_capacity_cost} slots"))
            if detail_item.lore:
                rows.append(("Lore", detail_item.lore))
            if self.selected_hero:
                ok, reason = can_equip(self.selected_hero, detail_item)
                rows.append(("Can equip", "Yes" if ok else f"No — {reason}"))

            KeyValueGrid(rows=rows, columns=1, column_width=520, row_gap=10,
                         label_color=theme.TEXT_MUTED, value_color=theme.TEXT_PRIMARY,
                         label_bold=True, value_bold=False, font_size=22, line_spacing=2,
                         ).draw(screen=screen, font=self.font, x=left_x, y=top_y)
        else:
            TextBlock(lines=["No item selected."], color=theme.TEXT_SECONDARY, row_spacing=24,
                      ).draw(screen, self.font, left_x, top_y, 520)

        if self.selected_hero is not None:
            hero = self.selected_hero
            syn_lines = synergy_summary_lines(hero)
            syn_text  = "; ".join(syn_lines) if syn_lines else "None active"
            loadout   = loadout_summary(hero)
            loadout_text = " | ".join(f"{c}: {n}" for c, n in loadout.items())

            KeyValueGrid(
                rows=[
                    ("Hero",      hero.name),
                    ("Class",     hero.hero_class + (f" / {hero.subclass}" if hero.subclass else "")),
                    ("Ability",   hero.special_ability or "None"),
                    ("Age",       str(hero.age)),
                    ("Level",     hero.level),
                    ("Power",     hero.combat_power()),
                    ("Capacity",  capacity_display(hero)),
                    ("Loadout",   loadout_text),
                    ("Synergies", syn_text),
                    ("Stats",     f"M {hero.total_stat('might')} | A {hero.total_stat('agility')} | Mi {hero.total_stat('mind')} | S {hero.total_stat('spirit')}"),
                ],
                columns=1, column_width=1040, row_gap=10,
                label_color=theme.TEXT_MUTED, value_color=theme.TEXT_PRIMARY,
                label_bold=True, value_bold=False, font_size=22, line_spacing=2,
            ).draw(screen=screen, font=self.font, x=right_x, y=top_y)
        else:
            TextBlock(lines=["No hero selected."], color=theme.TEXT_SECONDARY, row_spacing=24,
                      ).draw(screen, self.font, right_x, top_y, 1040)

    def build_buttons(self):
        buttons = [hub_button(self.on_return_to_hub)]
        if self.selected_item and self.selected_hero and not self.selected_item.consumable:
            ok, _ = can_equip(self.selected_hero, self.selected_item)
            if ok:
                buttons.append(action_button("Equip Item", self._equip_selected, rect=(1660, 956, 180, 44)))
        if self.selected_hero and self.selected_equipment_category:
            buttons.append(action_button("Unequip", self._unequip_selected, rect=(1460, 956, 180, 44)))
        return buttons

    def _handle_row_click(self, pos):
        item = self.items_panel.item_at_pos(pos)
        if item is not None:
            self.selected_item = item
            self.selected_equipment_category = None
            self.status_message = f"Selected: {item.name} [{item.category}]"
            return
        hero = self.heroes_panel.item_at_pos(pos)
        if hero is not None:
            self.selected_hero = hero
            self.selected_equipment_category = None
            self.status_message = f"Selected hero: {hero.name}"
            self.sync_lists()
            return
        eq_row = self.equipment_panel.item_at_pos(pos)
        if eq_row is not None:
            category, item = eq_row
            self.selected_equipment_category = category
            self.selected_item = None
            self.status_message = f"Selected equipped: {item.name} ({category})"

    def _equip_selected(self):
        if not self.selected_item or not self.selected_hero:
            self.status_message = "Select both an item and a hero."
            return
        result = equip_item(self.selected_hero, self.selected_item, self.state.inventory)
        self.status_message = result.message
        if result.success:
            self.selected_item = None
            self.sync_lists()
            if self.on_save_game: self.on_save_game()

    def _unequip_selected(self):
        if not self.selected_hero or not self.selected_equipment_category:
            self.status_message = "Select an equipped item to unequip."
            return
        result = unequip_item(self.selected_hero, self.selected_equipment_category, self.state.inventory)
        self.status_message = result.message
        if result.success:
            self.selected_equipment_category = None
            self.sync_lists()
            if self.on_save_game: self.on_save_game()

    def _hero_equipment_rows(self):
        if self.selected_hero is None: return []
        return list(self.selected_hero.equipment.items())

    def _selected_equipment_row(self):
        if self.selected_hero is None or self.selected_equipment_category is None: return None
        for row in self._hero_equipment_rows():
            if row[0] == self.selected_equipment_category: return row
        return None

    def _equipment_empty_text(self):
        if self.selected_hero is None: return "Select a hero to view their loadout."
        return f"{self.selected_hero.name} has no equipped items."

    def _total_equipped(self):
        return sum(len(hero.equipment) for hero in self.state.roster)

    def _health_chip_style(self, hero):
        status = hero.health_status()
        if status in ("DEAD", "CRITICAL"): return "danger"
        if status in ("WOUNDED", "HURT") or hero.injured_years_remaining > 0: return "warning"
        return "good"

    def _item_bonus_summary(self, item):
        if item is None: return "No item selected"
        parts = []
        for stat, value in item.stat_bonuses.items(): parts.append(f"+{value} {stat}")
        for damage, value in item.damage_type_bonus.items(): parts.append(f"+{int(value * 100)}% {damage} dmg")
        for enemy, value in item.enemy_type_bonus.items(): parts.append(f"+{int(value * 100)}% vs {enemy}")
        for enemy, value in item.enemy_type_resistance.items(): parts.append(f"-{int(value * 100)}% from {enemy}")
        return "; ".join(parts) if parts else "No bonuses"