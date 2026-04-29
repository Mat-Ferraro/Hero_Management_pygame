from pygame_ui import theme


class ItemSummaryBlock:
    def __init__(self, item):
        self.item = item

    def bonus_summary(self):
        item = self.item
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

    def draw(self, screen, title_font, font, rect):
        item = self.item
        x = rect.x + 12
        y = rect.y + 10

        screen.blit(title_font.render(f"{item.name} [{item.rarity}]", True, theme.TEXT_PRIMARY), (x, y))
        y += title_font.get_height() + 6

        screen.blit(font.render(f"Slot: {item.slot} | Value: {item.value}g", True, theme.TEXT_SECONDARY), (x, y))
        y += font.get_height() + 6

        screen.blit(font.render(self.bonus_summary(), True, theme.TEXT_MUTED), (x, y))