from pygame_ui import theme
from pygame_ui.widgets.key_value_grid import KeyValueGrid


class PartySummary:
    def __init__(self, party):
        self.party = list(party or [])

    def total_power(self):
        return sum(hero.combat_power() for hero in self.party)

    def total_mentorship(self):
        return sum(hero.mentorship_value() for hero in self.party)

    def total_cost(self):
        return sum(hero.wage_per_year for hero in self.party)

    def draw(self, screen, font, x, y):
        rows = [
            ("Heroes", len(self.party)),
            ("Power", self.total_power()),
            ("Mentor", self.total_mentorship()),
            ("Cost", f"{self.total_cost()}g"),
        ]

        screen.blit(font.render("Party Summary", True, theme.TEXT_PRIMARY), (x, y))
        y += font.get_height() + 8

        return KeyValueGrid(rows, columns=2, label_width=70, column_width=180).draw(screen, font, x, y)