import pygame


class Panel:
    def __init__(self, rect, title=""):
        self.rect = pygame.Rect(rect)
        self.title = title

    def draw(self, screen, title_font):
        pygame.draw.rect(screen, (38, 38, 46), self.rect, border_radius=10)
        pygame.draw.rect(screen, (80, 80, 95), self.rect, 2, border_radius=10)

        if self.title:
            title_surface = title_font.render(self.title, True, (255, 255, 255))
            screen.blit(title_surface, (self.rect.x + 16, self.rect.y + 12))