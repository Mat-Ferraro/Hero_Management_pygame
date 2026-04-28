import pygame
from pygame_ui.scenes.management_scene import ManagementScene


class App:
    def __init__(self, screen, state):
        self.screen = screen
        self.state = state
        self.clock = pygame.time.Clock()

        self.scene = ManagementScene(state)

    def run(self):
        running = True

        while running:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                self.scene.handle_event(event)

            self.scene.update(mouse_pos)

            self.screen.fill((28, 28, 32))
            self.scene.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(60)