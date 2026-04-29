import pygame

from game_state import create_game
from save_system import load_game, save_exists, save_game

from pygame_ui.dev_console import DevConsole
from pygame_ui.scenes.game_hub_scene import GameHubScene
from pygame_ui.scenes.main_menu_scene import MainMenuScene
from pygame_ui.scenes.management_scene import ManagementScene
from pygame_ui.scenes.expedition_scene import ExpeditionScene
from pygame_ui.scenes.expedition_run_scene import ExpeditionRunScene
from pygame_ui.scenes.inventory_scene import InventoryScene
from pygame_ui.scenes.market_scene import MarketScene
from pygame_ui.scenes.guild_upgrades_scene import GuildUpgradesScene
from pygame_ui.scenes.training_scene import TrainingScene


MIN_WINDOW_WIDTH = 1280
MIN_WINDOW_HEIGHT = 720
WINDOW_FLAGS = pygame.RESIZABLE


class App:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = None
        self.dev_console = DevConsole(self)

        self.show_main_menu()

    def show_main_menu(self):
        self.scene = MainMenuScene(
            on_start_new_game=self.start_new_game,
            on_load_game=self.load_game,
            on_quit=self.quit_game,
        )

    def start_new_game(self):
        self.state = create_game()
        self.show_game_hub("New game started.")

    def load_game(self):
        if not save_exists():
            print("No save file found.")
            return

        try:
            self.state = load_game()
        except Exception as exc:
            print(f"Failed to load game: {exc}")
            return

        self.show_game_hub("Loaded saved game.")

    def save_current_game(self):
        if self.state is None:
            return

        try:
            path = save_game(self.state)
            print(f"Saved game to {path}")
        except Exception as exc:
            print(f"Save failed: {exc}")

    def show_game_hub(self, status_message="Game hub."):
        self.scene = GameHubScene(
            state=self.state,
            on_open_guild=self.show_guild,
            on_open_expedition=self.show_expedition,
            on_open_inventory=self.show_inventory,
            on_open_market=self.show_market,
            on_open_training=self.show_training,
            on_open_upgrades=self.show_guild_upgrades,
            on_save_game=self.save_current_game,
            on_return_to_menu=self.show_main_menu,
            status_message=status_message,
        )

    def show_guild(self):
        self.scene = ManagementScene(
            state=self.state,
            on_return_to_hub=self.show_game_hub,
            on_save_game=self.save_current_game,
        )

    def show_expedition(self):
        self.scene = ExpeditionScene(
            state=self.state,
            on_return_to_hub=self.show_game_hub,
            on_start_expedition=self.show_expedition_run,
        )

    def show_expedition_run(self, party, dungeon):
        self.scene = ExpeditionRunScene(
            state=self.state,
            party=party,
            dungeon=dungeon,
            on_return_to_hub=self.show_game_hub,
            on_save_game=self.save_current_game,
        )

    def show_inventory(self):
        self.scene = InventoryScene(
            state=self.state,
            on_return_to_hub=self.show_game_hub,
            on_save_game=self.save_current_game,
        )

    def show_market(self):
        if not self.state.guild_upgrades.market_unlocked:
            self.show_game_hub("Market is locked. Buy the Open Guild Market upgrade first.")
            return

        self.scene = MarketScene(
            state=self.state,
            on_return_to_hub=self.show_game_hub,
            on_save_game=self.save_current_game,
        )

    def show_training(self):
        if self.state.guild_upgrades.training_hall_level <= 0:
            self.show_game_hub("Training Hall is locked. Buy the Build Training Hall upgrade first.")
            return

        self.scene = TrainingScene(
            state=self.state,
            on_return_to_hub=self.show_game_hub,
            on_save_game=self.save_current_game,
        )

    def show_guild_upgrades(self):
        self.scene = GuildUpgradesScene(
            state=self.state,
            on_return_to_hub=self.show_game_hub,
            on_save_game=self.save_current_game,
        )

    def quit_game(self):
        self.running = False

    def resize_window(self, width, height):
        clamped_width = max(MIN_WINDOW_WIDTH, width)
        clamped_height = max(MIN_WINDOW_HEIGHT, height)

        self.screen = pygame.display.set_mode(
            (clamped_width, clamped_height),
            WINDOW_FLAGS,
        )

    def run(self):
        while self.running:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue

                if event.type == pygame.VIDEORESIZE:
                    self.resize_window(event.w, event.h)
                    continue

                handled_by_console = self.dev_console.handle_event(event)
                if handled_by_console:
                    continue

                if not self.dev_console.is_open:
                    self.scene.handle_event(event)

            self.scene.update(mouse_pos)

            self.screen.fill((28, 28, 32))
            self.scene.draw(self.screen)
            self.dev_console.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(60)