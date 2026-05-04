import pygame

from game_state import refresh_contract_market
from systems.hero_progression import ensure_progression_fields


class DevConsole:
    def __init__(self, app):
        self.app = app
        self.is_open = False
        self.input_text = ""
        self.history = []

        self.font = pygame.font.SysFont(None, 22)
        self.small_font = pygame.font.SysFont(None, 20)

    def toggle(self):
        self.is_open = not self.is_open
        self.input_text = ""

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return False

        if event.key == pygame.K_F1:
            self.toggle()
            return True

        if not self.is_open:
            return False

        if event.key == pygame.K_ESCAPE:
            self.is_open = False
            self.input_text = ""
            return True

        if event.key == pygame.K_RETURN:
            self.execute_command(self.input_text.strip())
            self.input_text = ""
            return True

        if event.key == pygame.K_BACKSPACE:
            self.input_text = self.input_text[:-1]
            return True

        if event.unicode:
            self.input_text += event.unicode
            return True

        return True

    def wrap_text(self, text, font, max_width):
        words = text.split(" ")
        lines = []
        current = ""

        for word in words:
            test = current + (" " if current else "") + word
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        return lines

    def draw(self, screen):
        if not self.is_open:
            return

        overlay_rect = pygame.Rect(20, 20, 1240, 190)
        pygame.draw.rect(screen, (12, 12, 16), overlay_rect, border_radius=8)
        pygame.draw.rect(screen, (120, 120, 150), overlay_rect, 2, border_radius=8)

        title = "DEV CONSOLE — F1 close | Enter run | Esc close"
        screen.blit(self.font.render(title, True, (235, 235, 245)), (40, 38))

        prompt = f"> {self.input_text}"
        pygame.draw.rect(screen, (28, 28, 36), (40, 66, 1180, 30), border_radius=4)
        screen.blit(self.font.render(prompt, True, (210, 240, 210)), (50, 72))

        y = 105
        max_width = 1160

        for entry in self.history[-4:]:
            wrapped_lines = self.wrap_text(entry, self.small_font, max_width)

            for line in wrapped_lines:
                screen.blit(self.small_font.render(line, True, (200, 200, 215)), (40, y))
                y += 20

    def execute_command(self, command):
        if not command:
            return

        self.history.append(f"> {command}")

        try:
            message = self.run_command(command)
        except Exception as exc:
            message = f"ERROR: {exc}"

        self.history.append(message)

    def run_command(self, command):
        state = self.app.state
        if state is None:
            return "No active game state."

        parts = command.split()
        name = parts[0].lower()
        args = parts[1:]

        if name in ("help", "?"):
            return self.help_text()

        if name in ("money", "gold"):
            amount = self.require_int(args, "amount")
            state.gold += amount
            return f"Added {amount}g. Gold is now {state.gold}g."

        if name == "set_gold":
            amount = self.require_int(args, "amount")
            state.gold = amount
            return f"Gold set to {state.gold}g."

        if name == "unlock_market":
            state.guild_upgrades.market_unlocked = True
            return "Market unlocked."

        if name == "unlock_training":
            state.guild_upgrades.training_hall_level = max(1, state.guild_upgrades.training_hall_level)
            return f"Training Hall unlocked at level {state.guild_upgrades.training_hall_level}."

        if name == "training_level":
            value = self.require_int(args, "level")
            value = max(0, min(3, value))
            state.guild_upgrades.training_hall_level = value
            return f"Training Hall level set to {value}."

        if name in ("training_points", "add_tp", "tp_all"):
            amount = self.require_int(args, "amount")
            updated_count = 0

            for hero in state.roster:
                ensure_progression_fields(hero)
                hero.training_points += amount
                updated_count += 1

            return f"Added {amount} training point(s) to {updated_count} active roster hero(es)."

        if name == "unlock_all_classes":
            state.guild_upgrades.unlocked_classes = ["Warrior", "Rogue", "Cleric", "Mage"]
            refresh_contract_market(state)
            return "All classes unlocked and recruit market refreshed."

        if name == "upgrade_roster":
            value = self.require_int(args, "capacity")
            value = max(1, min(20, value))
            state.guild_upgrades.roster_capacity = value
            return f"Roster capacity set to {value}."

        if name == "upgrade_missions":
            value = self.require_int(args, "difficulty")
            value = max(1, min(5, value))
            state.guild_upgrades.mission_difficulty_cap = value
            return f"Mission difficulty cap set to {value}."

        if name == "upgrade_recruits":
            value = self.require_int(args, "level")
            value = max(1, min(20, value))
            state.guild_upgrades.recruit_level_cap = value
            refresh_contract_market(state)
            return f"Recruit level cap set to {value}; recruit market refreshed."

        if name == "stipend":
            value = self.require_int(args, "amount")
            value = max(0, value)
            state.guild_upgrades.crown_stipend = value
            return f"Crown stipend set to {value}g."

        if name == "unlock_all":
            state.guild_upgrades.market_unlocked = True
            state.guild_upgrades.training_hall_level = 3
            state.guild_upgrades.unlocked_classes = ["Warrior", "Rogue", "Cleric", "Mage"]
            state.guild_upgrades.roster_capacity = 20
            state.guild_upgrades.mission_difficulty_cap = 5
            state.guild_upgrades.recruit_level_cap = 20
            state.guild_upgrades.crown_stipend = 500
            refresh_contract_market(state)
            return "Unlocked all major dev test gates and refreshed recruits."

        if name == "upgrade_all":
            state.guild_upgrades.training_hall_level = 3
            state.guild_upgrades.roster_capacity = 20
            state.guild_upgrades.mission_difficulty_cap = 5
            state.guild_upgrades.recruit_level_cap = 20
            state.guild_upgrades.crown_stipend = 500
            return "All implemented guild upgrade values maxed."

        if name == "refresh_recruits":
            refresh_contract_market(state)
            return "Recruit market refreshed."

        if name == "heal_all":
            for hero in state.roster:
                hero.injured_years_remaining = 0
                hero.current_health = None
            return "All roster heroes healed."

        if name == "satisfy_all":
            for hero in state.roster:
                hero.satisfaction = 100
            return "All roster hero satisfaction set to 100."

        if name == "add_xp":
            amount = self.require_int(args, "amount")
            for hero in state.roster:
                hero.add_xp(amount)
            return f"Added {amount} XP to all roster heroes."

        if name == "level_all":
            level = self.require_int(args, "level")
            level = max(1, min(20, level))
            for hero in state.roster:
                hero.level = level
                hero.xp = 0
            return f"All roster heroes set to level {level}."

        if name == "age_all":
            years = self.require_int(args, "years")
            for hero in state.roster:
                hero.age += years
            return f"Aged all roster heroes by {years} years."

        if name == "save":
            self.app.save_current_game()
            return "Game saved."

        return f"Unknown command: {name}. Type help."

    def require_int(self, args, name):
        if not args:
            raise ValueError(f"Missing {name}.")
        return int(args[0])

    def help_text(self):
        return (
            "Commands: money N, set_gold N, unlock_market, unlock_training, training_level N, "
            "training_points N, add_tp N, tp_all N, unlock_all_classes, unlock_all, upgrade_all, "
            "upgrade_roster N, upgrade_missions N, upgrade_recruits N, stipend N, refresh_recruits, "
            "heal_all, satisfy_all, add_xp N, level_all N, age_all N, save"
        )