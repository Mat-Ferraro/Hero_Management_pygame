import pygame

from event_system import choose_event_for_enemy
from expedition_runner import finish_expedition
from manager_reputation import reputation_for_level_up
from pygame_ui.ui_helpers import clean_ansi_text, clamp_scroll, draw_scrollbar, truncate_text, wrap_text
from systems.campaign_cycle import CampaignCycleManager
from systems.combat_system import estimate_success_chance
from systems.room_system import (
    COMBAT_ROOM_TYPES,
    generate_room_options,
    resolve_event_choice,
    resolve_room,
)
from systems.survivor_system import remove_temporary_survivors_from_party

from ..widgets.button import Button
from ..widgets.panel import Panel


class ExpeditionRunScene:
    LOG_VISIBLE_ROWS = 9
    LOG_ROW_SPACING = 22

    CHOICE_ROW_HEIGHT = 62
    CHOICE_ROW_SPACING = 70

    def __init__(self, state, party, dungeon, on_return_to_hub, on_save_game):
        self.state = state
        self.party = party
        self.dispatched_heroes = list(party)
        self.dungeon = dungeon
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        self.font = pygame.font.SysFont(None, 22)
        self.small_font = pygame.font.SysFont(None, 20)
        self.title_font = pygame.font.SysFont(None, 28)
        self.header_font = pygame.font.SysFont(None, 30)

        self.mouse_pos = (0, 0)
        self.status_message = "Choose the next room."

        self.room_number = 1
        self.rooms_completed = 0
        self.loot_earned = 0
        self.xp_earned = 0

        self.room_options = []
        self.log_lines = []
        self.log_scroll = 0

        self.awaiting_continue = False
        self.awaiting_event_choice = False
        self.expedition_finished = False

        self.active_event = None
        self.active_event_room_option = None

        self.header_panel = Panel((20, 16, 1240, 86), "Expedition Run")
        self.choice_panel = Panel((20, 120, 520, 290), "Choose Path")
        self.party_panel = Panel((560, 120, 700, 290), "Party Status")
        self.log_panel = Panel((20, 430, 1240, 260), "Expedition Log")

        for hero in self.party:
            hero.reset_health_for_expedition()
            hero.participated_this_cycle = True

        self.log_lines.append(f"Expedition started: {self.dungeon.name}")
        self.generate_next_room_options()

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for button in self.build_buttons():
                if button.rect.collidepoint(event.pos):
                    button.on_click()
                    return

        elif event.type == pygame.MOUSEWHEEL:
            if self.log_panel.rect.collidepoint(self.mouse_pos):
                self.log_scroll -= event.y
                self.log_scroll = clamp_scroll(
                    self.log_scroll,
                    len(self.wrapped_log_lines()),
                    self.LOG_VISIBLE_ROWS,
                )

    def update(self, mouse_pos):
        self.mouse_pos = mouse_pos

    def draw(self, screen):
        screen.fill((28, 28, 32))

        self.header_panel.draw(screen, self.title_font)
        self.choice_panel.draw(screen, self.title_font)
        self.party_panel.draw(screen, self.title_font)
        self.log_panel.draw(screen, self.title_font)

        self.draw_header(screen)
        self.draw_choices(screen)
        self.draw_party(screen)
        self.draw_log(screen)

        for button in self.build_buttons():
            button.update(self.mouse_pos)
            button.draw(screen, self.font)

    def draw_header(self, screen):
        stats = (
            f"Gold: {self.state.gold}g    "
            f"Year: {self.state.year}    "
            f"Expedition: {self.state.expedition}    "
            f"Room: {min(self.room_number, self.dungeon.room_count)}/{self.dungeon.room_count}    "
            f"Loot: {self.loot_earned}g    XP: {self.xp_earned}"
        )

        screen.blit(self.header_font.render(stats, True, (235, 235, 240)), (40, 56))
        screen.blit(self.font.render(self.status_message, True, (180, 200, 230)), (760, 82))

    def draw_choices(self, screen):
        if self.expedition_finished:
            self.draw_choice_message(screen, "Expedition complete.")
            return

        if self.awaiting_event_choice:
            self.draw_event_choices(screen)
            return

        if self.awaiting_continue:
            self.draw_choice_message(screen, "Room resolved. Continue when ready, or retreat from the dungeon.")
            return

        y = 176
        for index, option in enumerate(self.room_options, start=1):
            row_rect = self.choice_row_rect(y)
            is_hovered = row_rect.collidepoint(self.mouse_pos)

            fill_color = (50, 50, 62) if is_hovered else (42, 42, 52)
            border_color = (110, 110, 135) if is_hovered else (70, 70, 86)

            pygame.draw.rect(screen, fill_color, row_rect, border_radius=8)
            pygame.draw.rect(screen, border_color, row_rect, 1, border_radius=8)

            text = f"{index}. {option.room_type}: {option.description}"

            if option.room_type in COMBAT_ROOM_TYPES:
                enemy_power = self.dungeon.room_enemy_power(self.room_number, option.room_type)
                enemy_type = self.dungeon.enemy_type_for_room(option.room_type)
                chance = estimate_success_chance(self.party, enemy_power, option.room_type, enemy_type)
                text += f" | Enemy {enemy_power} | Edge {chance * 100:.1f}%"

            wrapped = wrap_text(text, self.small_font, 320)

            line_y = row_rect.y + 9
            for line in wrapped[:2]:
                screen.blit(self.small_font.render(line, True, (220, 220, 230)), (row_rect.x + 12, line_y))
                line_y += 20

            y += self.CHOICE_ROW_SPACING

    def draw_event_choices(self, screen):
        if not self.active_event:
            self.draw_choice_message(screen, "No event loaded.")
            return

        name = self.active_event.get("name", "Unknown Event")
        description = self.active_event.get("description", "")

        screen.blit(self.font.render(f"Event: {name}", True, (235, 220, 180)), (44, 172))

        wrapped_description = wrap_text(description, self.small_font, 430)
        y = 200
        for line in wrapped_description[:2]:
            screen.blit(self.small_font.render(line, True, (220, 220, 230)), (44, y))
            y += 20

        y = 250
        for index, choice in enumerate(self.active_event.get("choices", []), start=1):
            label = choice.get("label", "Unknown choice")
            wrapped = wrap_text(f"{index}. {label}", self.small_font, 310)

            for line in wrapped[:2]:
                screen.blit(self.small_font.render(line, True, (210, 210, 220)), (58, y))
                y += 20

            y += 18

    def draw_choice_message(self, screen, message):
        wrapped = wrap_text(message, self.font, 430)
        y = 178

        for line in wrapped:
            screen.blit(self.font.render(line, True, (210, 210, 220)), (44, y))
            y += 24

    def draw_party(self, screen):
        if not self.party:
            screen.blit(self.font.render("No heroes remain.", True, (220, 120, 120)), (584, 178))
            return

        y = 176
        for hero in self.party[:6]:
            hp_text = "Ready"
            if hero.current_health is not None:
                hp_text = f"{hero.current_health}/{hero.max_health()} HP"

            line = (
                f"{hero.name} | {hero.hero_class} | Lv {hero.level} | "
                f"Pwr {hero.combat_power()} | {hp_text} | {hero.health_status()} | "
                f"Sat {hero.satisfaction}"
            )

            color = (210, 240, 210)
            if hero.health_status() in ("DEAD", "CRITICAL"):
                color = (240, 140, 140)
            elif hero.health_status() in ("WOUNDED", "HURT"):
                color = (235, 210, 130)

            rendered = truncate_text(line, self.font, 620)
            screen.blit(self.font.render(rendered, True, color), (584, y))
            y += 32

    def draw_log(self, screen):
        display_lines = self.wrapped_log_lines()
        visible = display_lines[self.log_scroll:self.log_scroll + self.LOG_VISIBLE_ROWS]

        y = 482
        for line in visible:
            screen.blit(self.font.render(line, True, (210, 210, 220)), (44, y))
            y += self.LOG_ROW_SPACING

        draw_scrollbar(
            screen=screen,
            font=self.font,
            panel=self.log_panel,
            scroll=self.log_scroll,
            item_count=len(display_lines),
            visible_count=self.LOG_VISIBLE_ROWS,
        )

    def build_buttons(self):
        buttons = [Button((1120, 40, 90, 32), "Hub", self.return_to_hub)]

        if self.expedition_finished:
            buttons.append(Button((350, 340, 150, 36), "Return to Hub", self.return_to_hub))
            return buttons

        if self.awaiting_event_choice:
            y = 248
            for choice in self.active_event.get("choices", []):
                buttons.append(
                    Button(
                        (390, y - 8, 110, 30),
                        "Choose",
                        lambda c=choice: self.resolve_event_choice_button(c),
                    )
                )
                y += 58

            return buttons

        if self.awaiting_continue:
            buttons.append(Button((230, 340, 120, 36), "Retreat", self.retreat))
            buttons.append(Button((370, 340, 120, 36), "Continue", self.continue_to_next_room))
            return buttons

        y = 176
        for option in self.room_options:
            row_rect = self.choice_row_rect(y)
            buttons.append(
                Button(
                    (row_rect.right - 116, row_rect.y + 16, 100, 30),
                    "Choose",
                    lambda o=option: self.resolve_room_choice(o),
                )
            )
            y += self.CHOICE_ROW_SPACING

        return buttons

    def generate_next_room_options(self):
        self.room_options = generate_room_options(self.dungeon, self.room_number)

    def resolve_room_choice(self, room_option):
        if room_option.room_type == "Event":
            self.active_event = choose_event_for_enemy(self.dungeon.enemy_type)
            self.active_event_room_option = room_option
            self.awaiting_event_choice = True
            self.status_message = "Choose an event response."
            return

        room_messages = [
            f"=== Room {self.room_number}: {room_option.room_type} ===",
            room_option.description,
        ]

        resolution = resolve_room(
            state=self.state,
            party=self.party,
            dungeon=self.dungeon,
            room_number=self.room_number,
            room_option=room_option,
        )

        self.apply_room_resolution(room_messages, resolution)

    def resolve_event_choice_button(self, choice):
        if not self.active_event or not self.active_event_room_option:
            self.status_message = "Event failed to resolve."
            return

        room_messages = [
            f"=== Room {self.room_number}: Event ===",
            self.active_event_room_option.description,
        ]

        resolution = resolve_event_choice(
            state=self.state,
            party=self.party,
            dungeon=self.dungeon,
            event=self.active_event,
            choice=choice,
        )

        self.awaiting_event_choice = False
        self.active_event = None
        self.active_event_room_option = None

        self.apply_room_resolution(room_messages, resolution)

    def apply_room_resolution(self, room_messages, resolution):
        room_messages.extend(resolution.messages)
        self.rooms_completed += 1

        if resolution.party_wiped:
            room_messages.append("Room rewards were not recovered because no heroes escaped.")
        else:
            self.loot_earned += resolution.loot
            self.xp_earned += resolution.xp
            self.state.gold += resolution.loot

            if resolution.loot > 0:
                room_messages.append(f"Gold after recovered room loot: {self.state.gold}g.")

        self.log_lines.extend(room_messages)
        self.scroll_log_to_bottom()

        if not self.party:
            self.log_lines.append("The expedition ends because the entire party is gone.")
            self.finish_expedition_run(completed=False)
            return

        if self.rooms_completed >= self.dungeon.room_count:
            self.finish_expedition_run(completed=True)
            return

        self.awaiting_continue = True
        self.status_message = "Room resolved."

    def continue_to_next_room(self):
        self.room_number += 1
        self.awaiting_continue = False
        self.status_message = "Choose the next room."
        self.generate_next_room_options()

    def retreat(self):
        self.log_lines.append(f"The party retreats after completing {self.rooms_completed} room(s).")
        self.finish_expedition_run(completed=False)

    def finish_expedition_run(self, completed):
        self.expedition_finished = True
        self.awaiting_continue = False
        self.awaiting_event_choice = False

        self.log_lines.append(f"Total recovered expedition loot: {self.loot_earned}g.")
        self.log_lines.append(f"Total recovered combat XP: {self.xp_earned}.")

        if completed and self.party:
            self.log_lines.append("The dungeon route was completed!")

        self.apply_xp_and_cleanup()

        cycle_manager = CampaignCycleManager(self.state)
        self.log_lines.extend(cycle_manager.advance_cycle(self.dispatched_heroes))

        self.log_lines.extend(finish_expedition(self.state, self.dungeon))

        if self.on_save_game is not None:
            self.on_save_game()

        self.status_message = "Expedition complete. Campaign cycle resolved and saved."
        self.scroll_log_to_bottom()

    def apply_xp_and_cleanup(self):
        for hero in list(self.party):
            if hero.is_temporary_survivor:
                continue

            old_level = hero.level
            xp_messages = hero.add_xp(self.xp_earned)

            for message in xp_messages:
                self.log_lines.append(message)

            if hero.level > old_level:
                for _ in range(hero.level - old_level):
                    self.log_lines.extend(reputation_for_level_up(self.state.reputation, hero.hero_class))

        self.log_lines.extend(remove_temporary_survivors_from_party(self.state, self.party))

    def return_to_hub(self):
        self.on_return_to_hub("Returned from expedition.")

    def wrapped_log_lines(self):
        display_lines = []

        for line in self.log_lines:
            clean = clean_ansi_text(line)
            wrapped = wrap_text(clean, self.font, 1120)

            if wrapped:
                display_lines.extend(wrapped)
            else:
                display_lines.append("")

        return display_lines

    def scroll_log_to_bottom(self):
        display_lines = self.wrapped_log_lines()
        self.log_scroll = clamp_scroll(
            max(0, len(display_lines) - self.LOG_VISIBLE_ROWS),
            len(display_lines),
            self.LOG_VISIBLE_ROWS,
        )

    def choice_row_rect(self, y):
        return pygame.Rect(44, y - 10, 470, self.CHOICE_ROW_HEIGHT)