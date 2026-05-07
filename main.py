import pygame

from pygame_ui.app import App


BASE_WINDOW_WIDTH = 1920
BASE_WINDOW_HEIGHT = 1080
WINDOW_FLAGS = pygame.RESIZABLE


def main() -> None:
    pygame.init()

    try:
        screen = pygame.display.set_mode(
            (BASE_WINDOW_WIDTH, BASE_WINDOW_HEIGHT),
            WINDOW_FLAGS,
        )
        pygame.display.set_caption("Hero Management")

        app = App(screen)
        app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()