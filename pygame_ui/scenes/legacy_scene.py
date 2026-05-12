"""
pygame_ui/scenes/legacy_scene.py

Hall of Legends — displays the guild's retirement legacy milestone tracks.

Shows:
  - Each class track with current tier and next milestone threshold.
  - Active bonus totals from all unlocked milestones.
  - List of retired heroes with class and age.
"""

from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.ui_helpers import truncate_text
from pygame_ui.widgets.card import Card
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.key_value_grid import KeyValueGrid
from pygame_ui.widgets.navigation_buttons import hub_button
from pygame_ui.widgets.resource_header import ResourceHeader
from pygame_ui.widgets.section_title import SectionTitle
from pygame_ui.widgets.status_chip import StatusChip
from pygame_ui.widgets.text_block import TextBlock
from pygame_ui.widgets.row_styles import draw_selectable_row
from pygame_ui.widgets.scrollable_list_panel import ScrollableListPanel
from systems.guild.retirement_legacy import (
    CLASS_MILESTONES,
    compute_legacy,
    legacy_summary_lines,
)


# Tier badge colours.
TIER_COLORS = {
    0: (80,  80,  90),   # none
    1: (140, 110, 60),   # bronze
    2: (160, 160, 170),  # silver
    3: (200, 170, 80),   # gold
}


class LegacyScene(SceneBase):
    def __init__(self, state, on_return_to_hub):
        super().__init__()

        self.state            = state
        self.on_return_to_hub = on_return_to_hub

        self.retired_panel = ScrollableListPanel(
            rect=(1140, 150, 720, 840),
            title="Retired Heroes",
            row_height=56, row_gap=8, visible_rows=None,
            font=self.font, title_font=self.title_font,
            padding=16, title_height=64,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def handle_event(self, event):
        if self.retired_panel.handle_event(event): return
        if self.handle_buttons_click(event, self.build_buttons()): return

    def update(self, mouse_pos):
        super().update(mouse_pos)
        self.retired_panel.set_items(list(getattr(self.state, "retired_heroes", [])))
        self.retired_panel.update(mouse_pos)

    def draw(self, screen):
        self.clear_screen(screen)
        legacy = compute_legacy(self.state)

        self.draw_header(screen, legacy)
        self.draw_milestone_tracks(screen, legacy)
        self.draw_bonus_summary(screen, legacy)
        self.retired_panel.set_items(list(getattr(self.state, "retired_heroes", [])))
        self.retired_panel.draw(screen=screen, row_drawer=self.draw_retired_row,
                                selected_item=None,
                                empty_text="No heroes have retired yet.")
        self.update_and_draw_buttons(screen, self.build_buttons())

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def draw_header(self, screen, legacy):
        retired_count = sum(legacy.retired_counts.values())

        HeaderPanel(
            rect=(40, 30, 1840, 96),
            title="Hall of Legends",
            stats="",
            status_message=f"{retired_count} heroes have retired with the guild.",
            stats_pos=(70, 70), status_pos=(980, 110),
        ).draw(screen, self.title_font, self.header_font, self.font)

        ResourceHeader(
            resources=[
                ("Retired",    retired_count),
                ("Stipend +",  f"{legacy.total_gold_stipend_bonus}g"),
                ("XP Bonus +", f"{legacy.total_xp_bonus_percent}%"),
                ("Recovery +", f"{legacy.total_injury_recovery} yr"),
                ("Morale +",   legacy.total_satisfaction_bonus),
            ],
            spacing=195, item_max_width=170, font_size=24,
            label_color=theme.TEXT_MUTED, value_color=theme.TEXT_PRIMARY,
            label_bold=False, value_bold=True,
        ).draw(screen, self.font, 60, 72)

    # ------------------------------------------------------------------
    # Milestone tracks
    # ------------------------------------------------------------------

    def draw_milestone_tracks(self, screen, legacy):
        Card(
            rect=(40, 150, 1060, 620),
            title="Milestone Tracks",
            lines=[],
            fill_color=theme.PANEL_BG,
            border_color=theme.PANEL_BORDER,
            padding=18,
        ).draw(screen, self.title_font, self.font)

        x     = 64
        y     = 220
        w     = 1012
        track_h = 130
        gap   = 16

        for hero_class, milestones in CLASS_MILESTONES.items():
            count   = legacy.retired_counts.get(hero_class, 0)
            tier    = legacy.milestone_tier(hero_class)
            nxt     = legacy.next_milestone(hero_class)

            # Track background.
            import pygame
            track_rect = pygame.Rect(x, y, w, track_h)
            pygame.draw.rect(screen, (38, 38, 48), track_rect, border_radius=10)
            pygame.draw.rect(screen, (72, 76, 92), track_rect, 1, border_radius=10)

            # Class name + tier badge.
            tier_color = TIER_COLORS.get(tier, TIER_COLORS[0])
            screen.blit(
                self.font.render(hero_class, True, tier_color),
                (x + 14, y + 10),
            )

            tier_label = f"Tier {tier}" if tier > 0 else "No Legacy"
            StatusChip(
                rect=(x + 120, y + 10, 80, 26),
                text=tier_label,
                style="good" if tier == 3 else ("info" if tier > 0 else "default"),
            ).draw(screen, self.small_font)

            screen.blit(
                self.small_font.render(f"{count} retired", True, theme.TEXT_MUTED),
                (x + 212, y + 16),
            )

            # Active milestone label.
            if tier > 0:
                active = max((m for m in milestones if count >= m.heroes_needed),
                             key=lambda m: m.tier, default=None)
                if active:
                    screen.blit(
                        self.font.render(active.label, True, theme.TEXT_PRIMARY),
                        (x + 14, y + 46),
                    )
                    screen.blit(
                        self.small_font.render(
                            truncate_text(active.description, self.small_font, w - 28),
                            True, theme.TEXT_MUTED,
                        ),
                        (x + 14, y + 74),
                    )
            else:
                screen.blit(
                    self.small_font.render("Retire your first hero of this class to begin.",
                                          True, theme.TEXT_MUTED),
                    (x + 14, y + 46),
                )

            # Next milestone progress.
            if nxt is not None:
                needed  = nxt.heroes_needed
                progress = min(1.0, count / needed)
                bar_x   = x + 14
                bar_y   = y + track_h - 22
                bar_w   = w - 28
                bar_h   = 10

                pygame.draw.rect(screen, (50, 50, 62), (bar_x, bar_y, bar_w, bar_h), border_radius=5)
                fill_w = max(0, int(bar_w * progress))
                if fill_w > 0:
                    pygame.draw.rect(screen, tier_color, (bar_x, bar_y, fill_w, bar_h), border_radius=5)

                label = f"Next: {nxt.label} ({count}/{needed} retired)"
                screen.blit(
                    self.small_font.render(label, True, theme.TEXT_MUTED),
                    (bar_x, bar_y - 18),
                )
            else:
                screen.blit(
                    self.small_font.render("All milestones unlocked.", True, (160, 200, 160)),
                    (x + 14, y + track_h - 30),
                )

            y += track_h + gap

    # ------------------------------------------------------------------
    # Bonus summary
    # ------------------------------------------------------------------

    def draw_bonus_summary(self, screen, legacy):
        Card(
            rect=(40, 790, 1060, 200),
            title="Active Legacy Bonuses",
            lines=[],
            fill_color=theme.PANEL_BG,
            border_color=theme.PANEL_BORDER,
            padding=18,
        ).draw(screen, self.title_font, self.font)

        if not legacy.has_any_legacy():
            TextBlock(
                lines=["Retire heroes to earn permanent guild bonuses."],
                color=theme.TEXT_MUTED, row_spacing=24,
            ).draw(screen, self.font, 64, 860, 1000)
            return

        rows = []
        if legacy.total_gold_stipend_bonus > 0:
            rows.append(("Crown Stipend", f"+{legacy.total_gold_stipend_bonus}g per cycle"))
        if legacy.total_xp_bonus_percent > 0:
            rows.append(("Mission XP", f"+{legacy.total_xp_bonus_percent}%"))
        if legacy.total_injury_recovery > 0:
            rows.append(("Injury Recovery", f"-{legacy.total_injury_recovery} year(s)"))
        if legacy.total_satisfaction_bonus > 0:
            rows.append(("Campaign Morale", f"+{legacy.total_satisfaction_bonus} satisfaction"))

        if not rows:
            rows = [("No bonuses yet", "—")]

        KeyValueGrid(
            rows=rows, columns=2, column_width=450, row_gap=14,
            label_color=theme.TEXT_MUTED, value_color=(180, 220, 180),
            label_bold=True, value_bold=True, font_size=22, line_spacing=2,
        ).draw(screen=screen, font=self.font, x=64, y=856)

    # ------------------------------------------------------------------
    # Retired hero rows
    # ------------------------------------------------------------------

    def draw_retired_row(self, screen, hero, row_rect, is_selected, is_hovered):
        draw_selectable_row(screen=screen, rect=row_rect, is_selected=False,
                            is_hovered=is_hovered, style="green")

        screen.blit(
            self.font.render(
                truncate_text(hero.name, self.font, row_rect.width - 140),
                True, (190, 220, 190),
            ),
            (row_rect.x + 12, row_rect.y + 8),
        )

        StatusChip(
            rect=(row_rect.right - 108, row_rect.y + 8, 96, 24),
            text=hero.hero_class,
            style="info",
        ).draw(screen, self.small_font)

        screen.blit(
            self.small_font.render(
                f"Lv {hero.level} | Retired age {hero.age}",
                True, theme.TEXT_MUTED,
            ),
            (row_rect.x + 12, row_rect.y + 32),
        )

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------

    def build_buttons(self):
        return [hub_button(self.on_return_to_hub)]