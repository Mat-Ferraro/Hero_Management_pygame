import pygame

from game_state import create_game
from save_system import load_game, save_exists, save_game

from pygame_ui.scenes.game_hub_scene import GameHubScene
from pygame_ui.scenes.main_menu_scene import MainMenuScene
from pygame_ui.scenes.management_scene import ManagementScene


class App:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = None

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

    def quit_game(self):
        self.running = False

    def run(self):
        while self.running:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue

                self.scene.handle_event(event)

            self.scene.update(mouse_pos)

            self.screen.fill((28, 28, 32))
            self.scene.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(60)