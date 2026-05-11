"""
pygame_ui/app.py

Top-level application: scene management and game lifecycle.

handle_campaign_complete() changes:
  - Derives heroes_who_died from state.fallen_heroes delta (heroes added
    during the campaign that are contracted, not temporaries).
  - Derives campaign_outcome from the runtime's completed vs expired task
    ratio: if all spawned tasks were completed → "success";
    if more than half expired/failed → "failure"; otherwise None.
  - Passes both into CampaignCycleManager.advance_cycle() so reputation
    triggers actually fire.
"""

import pygame

from core.game_state import (
    campaign_is_active,
    clear_campaign_runtime,
    create_game,
    start_campaign_runtime,
    stop_campaign_runtime,
)
from core.save_system import load_game, save_exists, save_game
from systems.guild.campaign_cycle import CampaignCycleManager
from systems.guild.rival_guilds import ensure_rival_guild_state

from pygame_ui.dev_console import DevConsole
from pygame_ui.scenes.campaign_map_scene import CampaignMapScene
from pygame_ui.scenes.game_hub_scene import GameHubScene
from pygame_ui.scenes.guild_upgrades_scene import GuildUpgradesScene
from pygame_ui.scenes.inventory_scene import InventoryScene
from pygame_ui.scenes.main_menu_scene import MainMenuScene
from pygame_ui.scenes.management_scene import ManagementScene
from pygame_ui.scenes.market_scene import MarketScene
from pygame_ui.scenes.mission_assignment_scene import MissionAssignmentScene
from pygame_ui.scenes.rival_guilds_scene import RivalGuildsScene
from pygame_ui.scenes.training_scene import TrainingScene


class App:
    def __init__(self, screen):
        self.screen = screen
        self.clock  = pygame.time.Clock()
        self.running = True
        self.state   = None
        self.dev_console = DevConsole(self)
        self.scene   = None

        self.show_main_menu()

    # ------------------------------------------------------------------
    # Menu / game lifecycle
    # ------------------------------------------------------------------

    def show_main_menu(self):
        self.scene = MainMenuScene(
            on_start_new_game=self.start_new_game,
            on_load_game=self.load_game,
            on_quit=self.quit_game,
        )

    def start_new_game(self):
        self.state = create_game()
        ensure_rival_guild_state(self.state)
        self.show_game_hub()

    def load_game(self):
        if not save_exists():
            print("No save file found.")
            return
        try:
            self.state = load_game()
            ensure_rival_guild_state(self.state)
        except Exception as exc:
            print(f"Failed to load game: {exc}")
            return
        self.show_game_hub()

    def save_current_game(self):
        if self.state is None:
            return
        try:
            path = save_game(self.state)
            print(f"Saved game to {path}")
        except Exception as exc:
            print(f"Save failed: {exc}")

    def quit_game(self):
        self.running = False

    # ------------------------------------------------------------------
    # Scene navigation
    # ------------------------------------------------------------------

    def show_game_hub(self, status_message=""):
        self.scene = GameHubScene(
            state=self.state,
            on_open_guild=self.show_guild,
            on_open_campaign=self.show_campaign,
            on_open_inventory=self.show_inventory,
            on_open_market=self.show_market,
            on_open_training=self.show_training,
            on_open_upgrades=self.show_guild_upgrades,
            on_open_rivals=self.show_rival_guilds,
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

    def show_campaign(self, status_message=""):
        if self.state is None:
            return
        if not campaign_is_active(self.state):
            start_campaign_runtime(self.state)
            self.save_current_game()
        self.scene = CampaignMapScene(
            state=self.state,
            on_campaign_complete=self.handle_campaign_complete,
            on_open_task=self.show_mission_assignment,
            on_save_game=self.save_current_game,
            status_message=status_message,
        )

    def show_mission_assignment(self, task_id):
        self.scene = MissionAssignmentScene(
            state=self.state,
            task_id=task_id,
            on_return_to_campaign=self.show_campaign,
            on_save_game=self.save_current_game,
        )

    def show_inventory(self):
        self.scene = InventoryScene(
            state=self.state,
            on_return_to_hub=self.show_game_hub,
            on_save_game=self.save_current_game,
        )

    def show_market(self):
        if self.state is None:
            return
        if not self.state.guild_upgrades.market_unlocked:
            self.show_game_hub()
            return
        self.scene = MarketScene(
            state=self.state,
            on_return_to_hub=self.show_game_hub,
            on_save_game=self.save_current_game,
        )

    def show_training(self):
        if self.state is None:
            return
        if self.state.guild_upgrades.training_hall_level <= 0:
            self.show_game_hub()
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

    def show_rival_guilds(self):
        self.scene = RivalGuildsScene(
            state=self.state,
            on_return_to_hub=self.show_game_hub,
            on_save_game=self.save_current_game,
        )

    # ------------------------------------------------------------------
    # Campaign completion
    # ------------------------------------------------------------------

    def handle_campaign_complete(self):
        if self.state is None:
            return

        runtime = getattr(self.state, "campaign_runtime", None)

        # Heroes who participated this cycle (for satisfaction / contracts).
        participating_heroes = [
            hero for hero in self.state.roster
            if getattr(hero, "participated_this_cycle", False)
        ]

        # Heroes who died during this campaign — contracted only, not
        # temporary survivors.  fallen_heroes accumulates during campaign
        # resolution; we take all of them as this session's casualties.
        heroes_who_died = [
            hero for hero in getattr(self.state, "fallen_heroes", [])
            if not getattr(hero, "is_temporary_survivor", False)
        ]

        # Derive campaign outcome from task completion ratio.
        # completed_task_ids and expired_task_ids are tracked by the runtime.
        campaign_outcome = self._derive_campaign_outcome(runtime)

        cycle_messages = CampaignCycleManager(self.state).advance_cycle(
            participating_heroes,
            heroes_who_died=heroes_who_died,
            campaign_outcome=campaign_outcome,
        )

        if runtime is not None:
            stop_campaign_runtime(self.state)
            clear_campaign_runtime(self.state)

        self.save_current_game()

        status_message = "Campaign cycle resolved."
        if cycle_messages:
            status_message = cycle_messages[-1]

        self.show_game_hub(status_message=status_message)

    @staticmethod
    def _derive_campaign_outcome(runtime) -> str | None:
        """
        Determine whether the campaign was a success or failure based on
        completed vs expired task counts from the runtime.

        Rules (conservative thresholds — adjust as balance requires):
          - "success"  : all spawned tasks completed (none expired/failed).
          - "failure"  : more tasks expired/failed than completed.
          - None       : mixed result — no reputation signal either way.

        Returns None if runtime is unavailable or no tasks were spawned.
        """
        if runtime is None:
            return None

        completed = len(list(getattr(runtime, "completed_task_ids", []) or []))
        expired   = len(list(getattr(runtime, "expired_task_ids",   []) or []))
        total     = int(getattr(runtime, "total_spawns", 0))

        if total <= 0:
            return None

        if expired == 0 and completed > 0:
            return "success"

        if expired > completed:
            return "failure"

        return None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        while self.running:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue

                handled_by_console = self.dev_console.handle_event(event)
                if handled_by_console:
                    continue

                if not self.dev_console.is_open and self.scene is not None:
                    self.scene.handle_event(event)

            if self.scene is not None:
                self.scene.update(mouse_pos)

                self.screen.fill((28, 28, 32))
                self.scene.draw(self.screen)
                self.dev_console.draw(self.screen)

                pygame.display.flip()

            self.clock.tick(60)