from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
CORE_DIR = PROJECT_ROOT / "core"

sys.path.insert(0, str(CORE_DIR))

import pygame

from pygame_ui.app import App


def main():
    pygame.init()

    screen = pygame.display.set_mode((1280, 720))
    pygame.display.set_caption("Hero Management")

    app = App(screen)
    app.run()

    pygame.quit()


if __name__ == "__main__":
    main()