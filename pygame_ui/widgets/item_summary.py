"""
pygame_ui/widgets/item_summary.py

Small inline item display block used by card and detail widgets.

Updated for new Item schema (v2):
  - Shows item.category instead of item.slot.
  - Adds tags line if tags exist.
  - Adds drawback line if drawbacks exist.
"""

from pygame_ui import theme


class ItemSummaryBlock:
    def __init__(self, item):
        self.item = item

    def bonus_summary(self) -> str:
        item  = self.item
        parts = []

        for stat, value in item.stat_bonuses.items():
            parts.append(f"+{value} {stat}")

        for damage, value in item.damage_type_bonus.items():
            parts.append(f"+{int(value * 100)}% {damage}")

        for enemy, value in item.enemy_type_bonus.items():
            parts.append(f"+{int(value * 100)}% vs {enemy}")

        for enemy, value in item.enemy_type_resistance.items():
            parts.append(f"-{int(value * 100)}% from {enemy}")

        return "; ".join(parts) if parts else "No bonuses"

    def draw(self, screen, title_font, font, rect) -> None:
        item = self.item
        x    = rect.x + 12
        y    = rect.y + 10

        # Name + rarity
        screen.blit(
            title_font.render(f"{item.name} [{item.rarity}]", True, theme.TEXT_PRIMARY),
            (x, y),
        )
        y += title_font.get_height() + 6

        # Category + value (was "Slot: ..." with old schema)
        cat_label = "Consumable" if item.consumable else item.category
        screen.blit(
            font.render(f"{cat_label} | Value: {item.value}g", True, theme.TEXT_SECONDARY),
            (x, y),
        )
        y += font.get_height() + 6

        # Bonus summary
        screen.blit(
            font.render(self.bonus_summary(), True, theme.TEXT_MUTED),
            (x, y),
        )
        y += font.get_height() + 4

        # Tags (only if present)
        if item.tags:
            screen.blit(
                font.render(f"Tags: {item.tag_list_display()}", True, theme.TEXT_MUTED),
                (x, y),
            )
            y += font.get_height() + 4

        # First drawback only (keep widget compact)
        if item.drawbacks:
            screen.blit(
                font.render(f"Drawback: {item.drawbacks[0]}", True, theme.TEXT_MUTED),
                (x, y),
            )