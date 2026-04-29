from pygame_ui import theme
from pygame_ui.widgets.meter_row import MeterRow
from pygame_ui.widgets.status_chip import StatusChip


class HeroSummaryBlock:
    def __init__(self, hero):
        self.hero = hero

    def status_style(self):
        if getattr(self.hero, "injured_years_remaining", 0) > 0:
            return "warning"

        status = self.hero.health_status()
        if status in ("DEAD", "CRITICAL"):
            return "danger"
        if status in ("WOUNDED", "HURT"):
            return "warning"
        return "good"

    def draw(self, screen, title_font, font, rect):
        hero = self.hero
        x = rect.x + 12
        y = rect.y + 10

        title = f"{hero.name} | {hero.hero_class} Lv {hero.level}"
        screen.blit(title_font.render(title, True, theme.TEXT_PRIMARY), (x, y))
        y += title_font.get_height() + 6

        chip = StatusChip((x, y, 100, 24), hero.health_status(), self.status_style())
        chip.draw(screen, font)

        screen.blit(font.render(f"Power {hero.combat_power()} | Age {hero.age} | {hero.career_stage()}", True, theme.TEXT_SECONDARY), (x + 116, y + 3))
        y += 34

        MeterRow("HP", hero.current_health or hero.max_health(), hero.max_health()).draw(
            screen, font, x, y, width=rect.width - 24, label_width=48
        )