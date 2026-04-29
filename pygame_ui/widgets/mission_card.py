from pygame_ui import theme
from pygame_ui.widgets.status_chip import StatusChip
from pygame_ui.widgets.timeline_strip import TimelineStrip


class MissionCard:
    def __init__(self, dungeon, selected=False):
        self.dungeon = dungeon
        self.selected = selected

    def draw(self, screen, title_font, font, rect):
        dungeon = self.dungeon
        x = rect.x + 12
        y = rect.y + 10

        screen.blit(title_font.render(dungeon.name, True, theme.TEXT_PRIMARY), (x, y))
        y += title_font.get_height() + 6

        StatusChip((x, y, 82, 24), f"Diff {dungeon.difficulty}", "warning" if dungeon.difficulty >= 3 else "info").draw(screen, font)
        StatusChip((x + 92, y, 110, 24), dungeon.enemy_type, "default").draw(screen, font)
        y += 34

        screen.blit(font.render(f"Loot {dungeon.loot_min}-{dungeon.loot_max}g | XP {dungeon.xp_reward}", True, theme.TEXT_SECONDARY), (x, y))
        y += 26

        TimelineStrip(
            rect=(x, y, rect.width - 24, 18),
            total_steps=max(1, dungeon.room_count),
            current_step=0,
        ).draw(screen)