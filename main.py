from pathlib import Path
import sys

import pygame

PROJECT_ROOT = Path(__file__).resolve().parent
CORE_DIR = PROJECT_ROOT / "core"

sys.path.insert(0, str(CORE_DIR))

from pygame_ui.app import App


BASE_WINDOW_WIDTH = 1920
BASE_WINDOW_HEIGHT = 1080
WINDOW_FLAGS = pygame.RESIZABLE


def main():
    pygame.init()

    screen = pygame.display.set_mode(
        (BASE_WINDOW_WIDTH, BASE_WINDOW_HEIGHT),
        WINDOW_FLAGS,
    )
    pygame.display.set_caption("Hero Management")

    app = App(screen)
    app.run()

    pygame.quit()


if __name__ == "__main__":
    main()