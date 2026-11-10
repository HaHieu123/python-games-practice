"""Main game loop, state machine, and dungeon rendering."""

import random
import sys
import time
from typing import Any

import pygame

from .audio_system import AudioSystem
from .achievements import AchievementTracker
from .boss import (
    BOSS_FLOORS,
    Boss,
    BossHealthBar,
    BossIntroScreen,
    draw_boss_telegraph,
)
from .boss_attacks import BossProjectile, create_boss_projectiles
from .enemy import Enemy
from .effects import (
    DamageText,
    Particle,
    Projectile,
    ScreenShake,
    spawn_damage_text,
    spawn_heal_particles,
    spawn_hit_particles,
)
from .game_over import GameOverScreen
from .game_options import GameOptions
from .hud import HUD
from .inventory_screen import InventoryScreen
from .main_menu import MainMenu
from .map_generator import DungeonMap, generate_dungeon
from .pause_menu import PauseMenu
from .player import Player
from .save_system import SaveError, has_save, load_game, save_game
from .shop_screen import ShopScreen
from .settings_screen import SettingsScreen
from .settings import (
    COLOR_BACKGROUND,
    COLOR_ENEMY,
    COLOR_FLOOR,
    COLOR_FLOOR_ALT,
    COLOR_STAIRS,
    COLOR_WALL,
    FLOOR_COUNT,
    FPS,
    GAME_TITLE,
    GameState,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TILE_SIZE,
    TileType,
    VIEW_COLUMNS,
    VIEW_ROWS,
)


class Game:
    """Owns the game state, event loop, and dungeon rendering."""

    def __init__(self) -> None:
        """Initialize Pygame resources and the initial main-menu state."""
        pygame.init()
        pygame.display.set_caption(GAME_TITLE)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.state = GameState.MENU
        self.settings_return_state = GameState.MENU
        self.running = True
        self.message = ""
        self.message_timer = 0.0
        self.volume = 0.7
        self._dragging_volume = False
        self.victory = False
        self.in_shop = False
        self.boss: Boss | None = None
        self.boss_intro = BossIntroScreen()
        self.boss_health_bar = BossHealthBar()
        self.boss_projectiles: list[BossProjectile] = []
        self.boss_clock = 0.0
        self.boss_death_timer = 0.0
        self.player_death_timer = 0.0
        self.boss_flash = 0.0
        self.boss_death_position: tuple[float, float] | None = None
        self.is_new_game_plus = False
        self.run_seconds = 0.0
        self.damage_dealt = 0
        self.damage_taken = 0
        self.ranged_hits = 0
        self.purchases = 0
        self.non_boss_kills = 0
        self.floor_damage_taken = 0
        self.floor = 1
        self.dungeon: DungeonMap | None = None
        self.player: Player | None = None
        self.enemies: list[Enemy] = []
        self.dead_enemies: list[Enemy] = []
        self.main_menu = MainMenu()
        self.hud = HUD()
        self.inventory_screen = InventoryScreen()
        self.pause_menu = PauseMenu()
        self.settings_screen = SettingsScreen()
        self.shop_screen = ShopScreen()
        self.game_over_screen = GameOverScreen()
        self.options = GameOptions()
        self.achievements = AchievementTracker()
        self.audio = AudioSystem()
        self.projectiles: list[Projectile] = []
        self.particles: list[Particle] = []
        self.damage_texts: list[DamageText] = []
        self.screen_shake = ScreenShake()
        self.shake_offset = (0, 0)
        self.muzzle_flash_position: tuple[float, float] | None = None
        self.effects_surface = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA,
        )
        self.shake_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.audio.start_music()
        self._set_volume(self.volume)

    def run(self) -> None:
        """Run the event/update/render loop at the configured frame rate."""
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self._handle_events()
            self._update(dt)
            self._draw()
            pygame.display.flip()
        self.audio.stop()
        pygame.quit()
        sys.exit()

    def _update(self, dt: float) -> None:
        """Advance gameplay, regeneration, and visual effects using frame time."""
        dt = max(0.0, dt)
        if self.state in {
            GameState.PLAYING, GameState.SHOP, GameState.BOSS_INTRO,
            GameState.BOSS_DEATH, GameState.PLAYER_DEATH,
        }:
            self.run_seconds += dt
        self.boss_clock += dt
        if self.state in (GameState.PLAYING, GameState.SHOP):
            self._update_message(dt)
        if self.state == GameState.PLAYING:
            self.shake_offset = self.screen_shake.update(dt)
            if (
                self.options.screen_shake
                and isinstance(self.boss, Boss)
                and self.boss.phase == 3
                and self.boss.alive
            ):
                self.screen_shake.trigger()
            if self.player is not None:
                healed = self.player.update(dt)
                if healed:
                    self.particles.extend(
                        spawn_heal_particles(
                            (self.player.x * TILE_SIZE + TILE_SIZE / 2,
                             self.player.y * TILE_SIZE + TILE_SIZE / 2),
                        )
                    )
                self.hud.update(dt, self.player)
                self.player.animation.speed_scale = self.options.animation_speed

            if self.dungeon is not None:
                for projectile in self.projectiles:
                    hit_enemy = projectile.update(dt, self.enemies, self.dungeon)
                    if hit_enemy is not None:
                        hp_before = hit_enemy.hp
                        defeated = hit_enemy.take_damage(projectile.damage)
                        actual_damage = hp_before - hit_enemy.hp
                        self.damage_dealt += actual_damage
                        self.ranged_hits += 1
                        impact = (
                            hit_enemy.x * TILE_SIZE + TILE_SIZE / 2,
                            hit_enemy.y * TILE_SIZE + TILE_SIZE / 2,
                        )
                        self.particles.extend(spawn_hit_particles(impact, 14))
                        if self.options.screen_shake:
                            self.screen_shake.trigger()
                        self.audio.play("attack")
                        if self.options.damage_numbers and actual_damage:
                            self.damage_texts.append(spawn_damage_text(impact, actual_damage))
                        if defeated and self.player is not None:
                            self.player.enemies_killed += 1
                            if isinstance(hit_enemy, Boss):
                                self._achievement_event("boss_slayer")
                                self._begin_boss_death(hit_enemy)
                            else:
                                self._remember_enemy_death(hit_enemy)
                                self.non_boss_kills += 1
                                self.player.add_gold(hit_enemy.gold_reward)
                                self.audio.play("defeat")
                                self._set_message(
                                    f"Defeated {hit_enemy.name}. +{hit_enemy.gold_reward} gold."
                                )
                            self._achievement_event("first_blood")
                self.enemies = [enemy for enemy in self.enemies if enemy.alive]
                self.projectiles = [
                    projectile for projectile in self.projectiles if projectile.alive
                ]

            if self.boss is not None and self.boss.alive:
                # Boss chỉ đổi trạng thái theo lượt; đạn của boss vẫn bay theo thời gian thực.
                self.boss.animation_clock += dt
                self.boss.animation.speed_scale = self.options.animation_speed
                self.boss.update_animation(dt)
                self.boss_health_bar.update(dt, self.boss)

            for projectile in self.boss_projectiles:
                previous_hp = self.player.hp if self.player is not None else 0
                if self.player is not None and self.dungeon is not None:
                    alive = projectile.update(dt, self.player, self.dungeon)
                    self.damage_taken += previous_hp - self.player.hp
                    self.floor_damage_taken += previous_hp - self.player.hp
                    if previous_hp > self.player.hp:
                        self._spawn_player_hurt()
                        if self.player.hp <= 0:
                            break
                    projectile.alive = alive
            self.boss_projectiles = [
                projectile for projectile in self.boss_projectiles
                if projectile.alive
            ]

            for enemy in self.enemies:
                if not isinstance(enemy, Boss):
                    if enemy.animation is not None:
                        enemy.animation.speed_scale = self.options.animation_speed
                    enemy.update_animation(dt)
            for enemy in self.dead_enemies:
                if enemy.animation is not None:
                    enemy.animation.speed_scale = self.options.animation_speed
                enemy.update_animation(dt)
            self.dead_enemies = [
                enemy for enemy in self.dead_enemies
                if enemy.animation is None or not enemy.animation.finished
            ]

        if self.state == GameState.BOSS_INTRO:
            if self.boss is not None:
                self.boss.animation_clock += dt
                self.boss.animation.speed_scale = self.options.animation_speed
                self.boss.update_animation(dt)
        if self.state == GameState.BOSS_DEATH:
            self.shake_offset = self.screen_shake.update(dt)
            slowed_dt = dt * 0.35
            self.boss_death_timer = max(0.0, self.boss_death_timer - dt)
            self.boss_flash = max(0.0, self.boss_flash - dt)
            if self.boss_death_timer > 0 and random.random() < dt * 20:
                self.particles.extend(
                    spawn_hit_particles(self.boss_death_position or (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), 8)
                )
            for particle in self.particles:
                particle.update(slowed_dt)
            self.particles = [particle for particle in self.particles if particle.alive]
            if self.boss_death_timer <= 0:
                defeated_boss = self.boss
                self.boss = None
                self.audio.start_music()
                self.state = GameState.PLAYING
                if defeated_boss is not None and defeated_boss.boss_id == "demon_chicken":
                    if self.player is not None:
                        self.player.floors_cleared = FLOOR_COUNT
                    self._end_run(victory=True)

        if self.state == GameState.PLAYER_DEATH:
            self.player_death_timer = max(0.0, self.player_death_timer - dt)
            if self.player is not None:
                self.player.animation.speed_scale = self.options.animation_speed
                self.player.update(dt)
            if self.player_death_timer <= 0:
                self._end_run(victory=False)

        if self.state in (GameState.PLAYING, GameState.SHOP):
            for particle in self.particles:
                particle.update(dt)
            for damage_text in self.damage_texts:
                damage_text.update(dt)
            self.particles = [particle for particle in self.particles if particle.alive]
            self.damage_texts = [text for text in self.damage_texts if text.alive]

    def _spawn_player_hurt(self) -> None:
        if self.player is not None:
            if self.player.hp <= 0:
                self._begin_player_death()
                return
            self.player.hurt_timer = 0.25
            self.player.animation.set_state("hurt", force=True)
            if self.options.screen_shake:
                self.screen_shake.trigger()

    def _begin_player_death(self) -> None:
        """Play the player's death animation before showing the run summary."""
        if self.player is None or self.state == GameState.PLAYER_DEATH:
            return
        self.player.animation.set_state("death", force=True)
        self.player.animation.speed_scale = self.options.animation_speed
        self.player_death_timer = 0.6
        self.boss_projectiles.clear()
        self.projectiles.clear()
        self.state = GameState.PLAYER_DEATH

    def _achievement_event(self, achievement_id: str) -> None:
        try:
            if self.achievements.unlock(achievement_id):
                title = self.achievements.all_unlocked()
                unlocked_title = next(name for item_id, name, _ in title if item_id == achievement_id)
                self._set_message(f"Achievement unlocked: {unlocked_title}")
        except OSError as error:
            self._set_message(str(error))

    def _handle_events(self) -> None:
        """Dispatch Pygame events to the active state."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._handle_key(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._dragging_volume = False
            elif event.type == pygame.MOUSEMOTION and self._dragging_volume:
                self._set_volume(self.settings_screen.set_volume_from_position(event.pos))

    def _handle_key(self, key: int) -> None:
        """Handle keyboard input according to the current game state."""
        if self.state == GameState.PLAYING:
            if key == pygame.K_ESCAPE:
                self.state = GameState.PAUSED
            elif key == pygame.K_i:
                self.state = GameState.INVENTORY
            elif key == pygame.K_f:
                self._fire_projectile()
            elif key in (pygame.K_w, pygame.K_UP):
                self._take_player_turn(0, -1)
            elif key in (pygame.K_s, pygame.K_DOWN):
                self._take_player_turn(0, 1)
            elif key in (pygame.K_a, pygame.K_LEFT):
                self._take_player_turn(-1, 0)
            elif key in (pygame.K_d, pygame.K_RIGHT):
                self._take_player_turn(1, 0)
        elif self.state == GameState.INVENTORY:
            if key in (pygame.K_i, pygame.K_ESCAPE):
                self.state = GameState.PLAYING
        elif self.state == GameState.PAUSED:
            if key == pygame.K_ESCAPE:
                self.state = GameState.PLAYING
        elif self.state == GameState.SETTINGS:
            if key == pygame.K_ESCAPE:
                self.state = self.settings_return_state
            elif key in (pygame.K_LEFT, pygame.K_DOWN):
                self._set_volume(self.volume - 0.05)
            elif key in (pygame.K_RIGHT, pygame.K_UP):
                self._set_volume(self.volume + 0.05)
            elif key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                actions = {
                    pygame.K_1: "animation_speed",
                    pygame.K_2: "screen_shake",
                    pygame.K_3: "damage_numbers",
                    pygame.K_4: "colorblind_mode",
                }
                self._toggle_option(actions[key])
        elif self.state == GameState.SHOP:
            action = self.shop_screen.action_for_key(key)
            if action:
                self._shop_action(action)
        elif self.state == GameState.BOSS_INTRO and key in (pygame.K_RETURN, pygame.K_SPACE):
            self.state = GameState.PLAYING
        elif self.state == GameState.BOSS_DEATH:
            return
        elif self.state == GameState.GAME_OVER:
            if key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self.state = GameState.MENU
            elif key == pygame.K_n:
                self._new_game()
        elif self.state == GameState.MENU:
            can_continue = has_save()
            if key in (pygame.K_UP, pygame.K_w):
                self.main_menu.move_selection(-1, can_continue, self.achievements.ng_plus_unlocked)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.main_menu.move_selection(1, can_continue, self.achievements.ng_plus_unlocked)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                action = self.main_menu.activate(can_continue, self.achievements.ng_plus_unlocked)
                if action:
                    self._menu_action(action)
            elif key == pygame.K_ESCAPE:
                self.running = False

    def _handle_click(self, position: tuple[int, int]) -> None:
        """Dispatch clicks to the active screen."""
        if self.state == GameState.MENU:
            action = self.main_menu.click(
                position, has_save(), self.achievements.ng_plus_unlocked,
            )
            if action:
                self._menu_action(action)
        elif self.state == GameState.INVENTORY:
            if self.inventory_screen.click(position):
                self.state = GameState.PLAYING
        elif self.state == GameState.PAUSED:
            self._pause_action(self.pause_menu.click(position))
        elif self.state == GameState.SETTINGS:
            if self.settings_screen.hit_slider(position):
                self._dragging_volume = True
                self._set_volume(self.settings_screen.set_volume_from_position(position))
            else:
                action = self.settings_screen.click(position)
                if action == "back":
                    self.state = self.settings_return_state
                elif action and action.startswith("toggle:"):
                    self._toggle_option(action.split(":", 1)[1])
        elif self.state == GameState.SHOP:
            self._shop_action(self.shop_screen.click(position))
        elif self.state == GameState.GAME_OVER:
            action = self.game_over_screen.click(position)
            if action == "new":
                self._new_game()
            elif action == "new_game_plus":
                self._new_game(is_new_game_plus=True)
            elif action == "menu":
                self.state = GameState.MENU

    def _menu_action(self, action: str) -> None:
        """Start, continue, or quit from the main menu."""
        if action == "new":
            self._new_game()
        elif action == "new_game_plus":
            self._new_game(is_new_game_plus=True)
        elif action == "continue":
            self._continue_game()
        elif action == "settings":
            self._open_settings()
        elif action == "quit":
            self.running = False

    def _pause_action(self, action: str | None) -> None:
        """Apply an action chosen from the pause menu."""
        if action == "resume":
            self.state = GameState.PLAYING
        elif action == "save":
            self._manual_save()
        elif action == "settings":
            self._open_settings()
        elif action == "menu":
            self.state = GameState.MENU

    def _open_settings(self) -> None:
        self.settings_return_state = self.state
        self.state = GameState.SETTINGS

    def _toggle_option(self, option: str) -> None:
        try:
            if option == "animation_speed":
                self.options.cycle_animation_speed()
            else:
                self.options.toggle(option)
        except (OSError, KeyError) as error:
            self._set_message(f"Could not update option: {error}")

    def _set_volume(self, value: float) -> None:
        """Clamp and apply the master volume to Pygame's audio mixer."""
        self.volume = max(0.0, min(1.0, value))
        self.audio.set_volume(self.volume)

    def _new_game(self, is_new_game_plus: bool = False) -> None:
        """Create a new run with a generated first-floor dungeon."""
        self.floor = 1
        self.boss = None
        self.boss_projectiles.clear()
        self.is_new_game_plus = is_new_game_plus
        self.run_seconds = 0.0
        self.damage_dealt = 0
        self.damage_taken = 0
        self.ranged_hits = 0
        self.purchases = 0
        self.non_boss_kills = 0
        self.floor_damage_taken = 0
        self.boss_death_timer = 0.0
        self.player_death_timer = 0.0
        self.boss_projectiles.clear()
        self.dungeon = generate_dungeon()
        start_x, start_y = self.dungeon.start
        self.player = Player(start_x, start_y)
        self.enemies = self._spawn_enemies(self.dungeon, self.floor, is_new_game_plus)
        self.dead_enemies.clear()
        self.projectiles.clear()
        self.particles.clear()
        self.damage_texts.clear()
        self.muzzle_flash_position = None
        self.state = GameState.PLAYING
        self.victory = False
        self.in_shop = False
        self.audio.start_music()
        self.message = "Find the stairs. Enemies act after every move."
        self.message_timer = 4.0

    def _continue_game(self) -> None:
        """Load a saved run and report malformed saves without crashing."""
        try:
            data = load_game()
            if data is None:
                self.message = "No saved game was found."
                return
            self._restore_game(data)
            if self.boss is not None and data.get("boss_intro_pending"):
                self.state = GameState.BOSS_INTRO
            else:
                self.state = GameState.SHOP if self.in_shop else GameState.PLAYING
        except (SaveError, KeyError, TypeError, ValueError) as error:
            self.message = f"Could not continue: {error}"
            self.message_timer = 5.0

    def _restore_game(self, data: dict[str, Any]) -> None:
        """Restore dungeon, player, floor, and enemies from save data."""
        self.floor = int(data["floor"])
        self.player = Player.from_dict(data["player"])
        self.dungeon = DungeonMap.from_dict(data["dungeon"])
        self.enemies = [Enemy.from_dict(item) for item in data["enemies"]]
        self.dead_enemies.clear()
        self.in_shop = bool(data.get("in_shop", False))
        self.is_new_game_plus = bool(data.get("is_new_game_plus", False))
        self.run_seconds = float(data.get("run_seconds", 0.0))
        self.damage_dealt = int(data.get("damage_dealt", 0))
        self.damage_taken = int(data.get("damage_taken", 0))
        self.non_boss_kills = int(data.get("non_boss_kills", self.player.enemies_killed))
        self.floor_damage_taken = int(data.get("floor_damage_taken", 0))
        boss_data = data.get("boss")
        self.boss = Boss.from_state(boss_data) if isinstance(boss_data, dict) else None
        if self.boss is not None:
            self.boss_health_bar.ratio = max(0.0, self.boss.hp / self.boss.max_hp)
            self.enemies.append(self.boss)
            self.state = GameState.BOSS_INTRO if bool(data.get("boss_intro_pending", False)) else GameState.PLAYING
            self.audio.start_boss_music()
        else:
            self.audio.start_music()
        self.boss_projectiles.clear()
        self.projectiles.clear()
        self.particles.clear()
        self.damage_texts.clear()

    def _new_floor(self) -> None:
        """Complete a floor and open the intermission shop."""
        if self.player is None:
            return
        if self.floor_damage_taken == 0:
            self._achievement_event("survivor")
        if self.floor >= FLOOR_COUNT:
            self.player.floors_cleared = FLOOR_COUNT
            self._end_run(victory=True)
            return
        self.player.floors_cleared = self.floor
        self.in_shop = True
        self.state = GameState.SHOP
        self.projectiles.clear()
        self.boss_projectiles.clear()
        self.audio.play("stairs")
        self._set_message("The Wayfarer's Rest is open. Prepare for the next floor.")
        try:
            self._save()
        except SaveError as error:
            self._set_message(f"Shop opened, but autosave failed: {error}")

    def _leave_shop(self) -> None:
        """Spend no resources and begin the next generated floor."""
        if self.player is None:
            return
        self.in_shop = False
        self.floor += 1
        self.floor_damage_taken = 0
        self.dungeon = generate_dungeon()
        self.player.x, self.player.y = self.dungeon.start
        self.enemies = self._spawn_enemies(self.dungeon, self.floor, self.is_new_game_plus)
        self.dead_enemies.clear()
        self.boss = None
        boss_class = BOSS_FLOORS.get(self.floor)
        if boss_class is not None:
            rooms = sorted(
                self.dungeon.rooms[:-1] or self.dungeon.rooms,
                key=lambda room: abs(room.center[0] - self.player.x) + abs(room.center[1] - self.player.y),
                reverse=True,
            )
            boss_x, boss_y = rooms[0].center
            self.boss = boss_class(
                boss_x, boss_y,
                is_new_game_plus=self.is_new_game_plus,
            )
            self.enemies = [
                enemy for enemy in self.enemies
                if (enemy.x, enemy.y) != (boss_x, boss_y)
            ]
            self.enemies.append(self.boss)
            self.boss_health_bar.ratio = 1.0
            self.audio.start_boss_music()
        self.projectiles.clear()
        self.particles.clear()
        self.damage_texts.clear()
        self.boss_projectiles.clear()
        self.state = GameState.BOSS_INTRO if self.boss is not None else GameState.PLAYING
        if self.boss is not None:
            self.boss_clock = 0.0
        try:
            # Checkpoint is persisted after generating the boss floor and before the intro.
            self._save()
            if self.boss is None:
                self._set_message(f"Floor {self.floor}. Progress autosaved.")
        except SaveError as error:
            self._set_message(f"Floor changed, but autosave failed: {error}")

    def _shop_action(self, action: str | None) -> None:
        """Process shop purchases or continue to the next floor."""
        if self.state != GameState.SHOP or self.player is None or action is None:
            return
        if action == "continue":
            self._leave_shop()
            return

        costs = self._shop_prices()
        cost = costs.get(action)
        if cost is None:
            return
        if self.player.gold < cost:
            self.audio.play("error")
            self._set_message("Not enough gold.")
            return

        if action == "heal":
            restored = self.player.use_potion()
            if restored == 0:
                self.audio.play("error")
                self._set_message("Your vitality is already full.")
                return
            self.particles.extend(
                spawn_heal_particles(
                    (self.player.x * TILE_SIZE + TILE_SIZE / 2,
                     self.player.y * TILE_SIZE + TILE_SIZE / 2),
                    count=10,
                )
            )
            self._set_message(f"Restored {restored} vitality.")
        elif action == "attack":
            self.player.atk += 2
            self._set_message("Your attack increased by 2.")
        elif action == "defense":
            self.player.defense += 1
            self._set_message("Your defense increased by 1.")

        self.player.gold -= cost
        self.purchases += 1
        if self.purchases >= 5:
            self._achievement_event("collector")
        self.audio.play("purchase")
        try:
            self._save()
        except SaveError as error:
            self._set_message(f"Purchase made, but autosave failed: {error}")

    def _shop_prices(self) -> dict[str, int]:
        """Return current prices, with permanent upgrades costing more each time."""
        if self.player is None:
            return {"heal": 15, "attack": 35, "defense": 35}
        return {
            "heal": 15,
            "attack": 35 + max(0, self.player.atk - 12) * 8,
            "defense": 35 + max(0, self.player.defense - 3) * 12,
        }

    def _spawn_enemies(
        self,
        dungeon: DungeonMap,
        floor: int,
        is_new_game_plus: bool = False,
    ) -> list[Enemy]:
        """Create enemies on floor tiles away from the player start."""
        rng = random.Random()
        positions = [
            (x, y)
            for y in range(dungeon.height)
            for x in range(dungeon.width)
            if dungeon.is_walkable(x, y)
            and max(abs(x - dungeon.start[0]), abs(y - dungeon.start[1])) >= 7
            and (x, y) != dungeon.stairs
        ]
        rng.shuffle(positions)
        enemies: list[Enemy] = []
        multiplier = 1.5 if is_new_game_plus else 1.0
        for index, (x, y) in enumerate(positions[: 5 + floor * 2]):
            enemy_type = ("slime", "bat", "skeleton")[index % 3]
            hp = round((20 + floor * 7 + (10 if index % 2 else 0)) * multiplier)
            attack = round((5 + floor * 2) * multiplier)
            enemies.append(
                Enemy(
                    x=x,
                    y=y,
                    name={"slime": "Cave slime", "bat": "Cave bat", "skeleton": "Skeleton"}[enemy_type],
                    hp=hp,
                    atk=attack,
                    gold_reward=(5 + floor) * (2 if is_new_game_plus else 1),
                    enemy_type=enemy_type,
                )
            )
        return enemies

    def _take_player_turn(self, dx: int, dy: int) -> None:
        """Move or attack, then let all living enemies take their turn."""
        if self.player is None or self.dungeon is None:
            return
        self.player.face(dx, dy)
        target_x, target_y = self.player.x + dx, self.player.y + dy
        target_enemy = next(
            (enemy for enemy in self.enemies if enemy.alive and (enemy.x, enemy.y) == (target_x, target_y)),
            None,
        )
        if target_enemy is not None:
            self.audio.play("attack")
            self.player.set_animation_state("attack", force=True)
            previous_hp = target_enemy.hp
            if isinstance(target_enemy, Boss):
                defeated = target_enemy.take_damage(self.player.atk, melee=True)
            else:
                defeated = target_enemy.take_damage(self.player.atk)
            actual_damage = previous_hp - target_enemy.hp
            self.damage_dealt += actual_damage
            if self.options.damage_numbers and actual_damage:
                self.damage_texts.append(
                    spawn_damage_text(
                        (target_enemy.x * TILE_SIZE + 16, target_enemy.y * TILE_SIZE + 16),
                        actual_damage,
                    )
                )
            if defeated:
                self.player.enemies_killed += 1
                self._achievement_event("first_blood")
                if isinstance(target_enemy, Boss):
                    self._begin_boss_death(target_enemy)
                    return
                else:
                    self._remember_enemy_death(target_enemy)
                    self.non_boss_kills += 1
                    self.player.add_gold(target_enemy.gold_reward)
                    self._set_message(f"Defeated {target_enemy.name}. +{target_enemy.gold_reward} gold.")
                    self.audio.play("defeat")
        elif self.dungeon.is_walkable(target_x, target_y):
            tile = self.dungeon.tiles[target_y][target_x]
            if tile == TileType.STAIRS_DOWN:
                if self.boss is not None and self.boss.alive:
                    self._set_message("Defeat the floor guardian before descending.")
                    return
                self._new_floor()
                return
            self.player.x, self.player.y = target_x, target_y
            self.player.set_animation_state("walk", force=True)
        else:
            return

        self._advance_enemy_turn()

    def _advance_enemy_turn(self) -> None:
        """Let each living enemy act once after a successful player action."""
        if self.player is None or self.dungeon is None:
            return
        hp_before = self.player.hp
        pending_summons: list[Enemy] = []
        for enemy in self.enemies:
            if isinstance(enemy, Boss):
                if not enemy.alive:
                    continue
                result = enemy.take_boss_turn(self.player, self.dungeon)
                if result.attack:
                    self.audio.play("enemy_attack")
                    self._set_message(f"{enemy.title}: {result.attack.replace('_', ' ').upper()}!")
                if result.damage:
                    self.player.take_damage(result.damage)
                if self.player.hp < hp_before:
                    self._spawn_player_hurt()
                pending_summons.extend(result.summons)
                if result.shots:
                    origin = (
                        enemy.x * TILE_SIZE + 16,
                        enemy.y * TILE_SIZE + 16,
                    )
                    target = (
                        self.player.x * TILE_SIZE + 16,
                        self.player.y * TILE_SIZE + 16,
                    )
                    attack = result.attack or ""
                    count = len(result.shots)
                    color = (160, 229, 106) if attack == "acid_spit" else (227, 220, 187) if attack == "bone_volley" else (241, 150, 78)
                    self.boss_projectiles.extend(
                        create_boss_projectiles(
                            origin,
                            target,
                            result.shots[0][2],
                            count,
                            32 if count > 1 else 0,
                            color,
                        )
                    )
                if result.phase_changed:
                    self.boss_flash = 0.6
                    if self.options.screen_shake:
                        self.screen_shake.trigger()
                if self.player.hp <= 0:
                    damage = hp_before - self.player.hp
                    self.damage_taken += damage
                    self.floor_damage_taken += damage
                    self._begin_player_death()
                    return
                continue
            player_hp_before = self.player.hp
            if enemy.take_turn(self.dungeon, self.player):
                self.audio.play("enemy_attack")
                enemy.animation_action = "attack"
                enemy.animation_action_time = 0.35
            if self.player.hp < player_hp_before:
                self._spawn_player_hurt()
            if self.player.hp <= 0:
                damage = hp_before - self.player.hp
                self.damage_taken += damage
                self.floor_damage_taken += damage
                self._begin_player_death()
                return
        self.enemies = [enemy for enemy in self.enemies if enemy.alive]
        self.enemies.extend(pending_summons)
        self.damage_taken += hp_before - self.player.hp
        self.floor_damage_taken += hp_before - self.player.hp
        if self.player.hp <= 0:
            self._begin_player_death()

    def _remember_enemy_death(self, enemy: Enemy) -> None:
        """Keep ordinary defeated enemies briefly so their death animation can play."""
        if not isinstance(enemy, Boss) and all(dead is not enemy for dead in self.dead_enemies):
            self.dead_enemies.append(enemy)

    def _begin_boss_death(self, boss: Boss) -> None:
        """Start the layered boss explosion and record its rewards."""
        self.boss_death_position = (boss.x * TILE_SIZE + 16, boss.y * TILE_SIZE + 16)
        self.boss_death_timer = 2.5
        self.boss_flash = 0.6
        self.state = GameState.BOSS_DEATH
        self.particles.extend(spawn_hit_particles(self.boss_death_position, 32))
        self.damage_texts.clear()
        self.boss_projectiles.clear()
        if self.player is not None:
            self.player.add_gold(boss.gold_reward)
            self._achievement_event("boss_slayer")
            if boss.boss_id == "demon_chicken" and self.floor_damage_taken == 0:
                self._achievement_event("survivor")
            self.enemies = [enemy for enemy in self.enemies if enemy is not boss]
            if boss.boss_id == "demon_chicken":
                self._achievement_event("champion")
        if self.options.screen_shake:
            self.screen_shake.trigger()

    def _fire_projectile(self) -> None:
        """Fire one homing bolt at the nearest enemy within fourteen tiles."""
        if self.player is None or self.dungeon is None:
            return
        targets = [
            enemy for enemy in self.enemies
            if enemy.alive
            and ((enemy.x - self.player.x) ** 2 + (enemy.y - self.player.y) ** 2) ** 0.5 <= 14
        ]
        if not targets:
            self.audio.play("error")
            self._set_message("No enemy in ranged attack distance.")
            return

        target = min(
            targets,
            key=lambda enemy: (enemy.x - self.player.x) ** 2 + (enemy.y - self.player.y) ** 2,
        )
        dx, dy = target.x - self.player.x, target.y - self.player.y
        self.player.face(dx, dy)
        start = (
            self.player.x * TILE_SIZE + TILE_SIZE / 2,
            self.player.y * TILE_SIZE + TILE_SIZE / 2,
        )
        direction = pygame.Vector2(dx, dy)
        direction.scale_to_length(18)
        muzzle = (start[0] + direction.x, start[1] + direction.y)
        self.muzzle_flash_position = muzzle
        self.projectiles.append(
            Projectile(x=muzzle[0], y=muzzle[1], target=target, damage=self.player.atk)
        )
        self.audio.play("attack")
        self._advance_enemy_turn()

    def _end_run(self, victory: bool) -> None:
        """Move to the run summary after a win or defeat."""
        self.state = GameState.GAME_OVER
        self.victory = victory
        self.audio.play("victory" if victory else "defeat")
        if victory:
            if self.run_seconds < 600:
                self._achievement_event("speedrun")
            if self.non_boss_kills == 0:
                self._achievement_event("pacifist")
            if self.player is not None and self.player.gold_earned >= 250:
                self._achievement_event("treasure_hunter")
            if self.ranged_hits >= 10:
                self._achievement_event("archer")
            if self.damage_taken == 0:
                self._achievement_event("survivor")
            self._achievement_event("new_game_plus")
        if victory:
            self._set_message(f"Victory! You conquered all {FLOOR_COUNT} floors.")
        else:
            self._set_message("You have fallen in the dungeon.")

    def _save(self) -> None:
        """Serialize the current run to the save system."""
        if self.player is None or self.dungeon is None:
            raise SaveError("There is no active run to save.")
        data = {
            "floor": self.floor,
            "player": self.player.to_dict(),
            "dungeon": self.dungeon.to_dict(),
            "enemies": [
                enemy.to_dict() for enemy in self.enemies
                if enemy.alive and not isinstance(enemy, Boss)
            ],
            "in_shop": self.in_shop,
            "boss": self.boss.serialize_boss() if self.boss is not None else None,
            "boss_intro_pending": self.state == GameState.BOSS_INTRO,
            "is_new_game_plus": self.is_new_game_plus,
            "run_seconds": self.run_seconds,
            "damage_dealt": self.damage_dealt,
            "damage_taken": self.damage_taken,
            "non_boss_kills": self.non_boss_kills,
            "floor_damage_taken": self.floor_damage_taken,
        }
        save_game(data)

    def _manual_save(self) -> None:
        """Save the current run and display an explicit success or error."""
        try:
            self._save()
            self._set_message("Game saved.")
        except SaveError as error:
            self._set_message(f"Save failed: {error}")

    def _set_message(self, message: str) -> None:
        """Show a short status message on the HUD."""
        self.message = message
        self.message_timer = 3.0

    def _update_message(self, dt: float) -> None:
        """Count down the current transient HUD message."""
        self.message_timer = max(0.0, self.message_timer - dt)

    def _draw(self) -> None:
        """Draw the active screen."""
        self.screen.fill(COLOR_BACKGROUND)
        if self.state == GameState.MENU:
            self.main_menu.draw(
                self.screen,
                can_continue=has_save(),
                can_new_game_plus=self.achievements.ng_plus_unlocked,
                message=self.message,
                message_timer=self.message_timer,
            )
        elif self.state == GameState.PLAYING:
            self._draw_game()
        elif self.state == GameState.INVENTORY:
            self._draw_game()
            if self.player is not None:
                self.inventory_screen.draw(self.screen, self.player)
        elif self.state == GameState.PAUSED:
            self._draw_game()
            self.pause_menu.draw(self.screen, self.message if self.message_timer > 0 else "")
        elif self.state == GameState.SETTINGS:
            if self.settings_return_state in (GameState.PAUSED, GameState.INVENTORY):
                self._draw_game()
            else:
                self.screen.fill(COLOR_BACKGROUND)
            self.settings_screen.draw(self.screen, self.volume, self.options)
        elif self.state == GameState.SHOP:
            self._draw_game()
            if self.player is not None:
                prices = self._shop_prices()
                self.shop_screen.draw(
                    self.screen,
                    self.player,
                    self.floor + 1,
                    prices["heal"],
                    prices["attack"],
                    prices["defense"],
                    self.message if self.message_timer > 0 else "",
                )
        elif self.state == GameState.GAME_OVER:
            if self.player is not None:
                self.game_over_screen.draw(
                    self.screen,
                    self.player,
                    self.victory,
                    self.run_seconds,
                    self.damage_dealt,
                    self.damage_taken,
                    self.is_new_game_plus,
                )
        elif self.state in {
            GameState.BOSS_INTRO, GameState.BOSS_DEATH, GameState.PLAYER_DEATH,
        }:
            self._draw_game()
            if self.state == GameState.BOSS_INTRO and self.boss is not None:
                self.boss_intro.draw(self.screen, self.boss)
            elif self.state == GameState.BOSS_DEATH:
                flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                alpha = round(140 * min(1.0, self.boss_flash / 0.6))
                flash.fill((255, 232, 202, alpha))
                self.screen.blit(flash, (0, 0))

    def _draw_game(self) -> None:
        """Draw the visible dungeon, entities, HUD, and minimap."""
        if self.dungeon is None or self.player is None:
            return
        camera_x = max(0, min(self.player.x - VIEW_COLUMNS // 2, self.dungeon.width - VIEW_COLUMNS))
        camera_y = max(0, min(self.player.y - VIEW_ROWS // 2, self.dungeon.height - VIEW_ROWS))
        for screen_y in range(VIEW_ROWS):
            map_y = camera_y + screen_y
            for screen_x in range(VIEW_COLUMNS):
                map_x = camera_x + screen_x
                tile = self.dungeon.tiles[map_y][map_x]
                rect = pygame.Rect(screen_x * TILE_SIZE, screen_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if tile == TileType.WALL:
                    pygame.draw.rect(self.screen, COLOR_WALL, rect)
                elif tile == TileType.STAIRS_DOWN:
                    pygame.draw.rect(self.screen, COLOR_FLOOR, rect)
                    center = rect.center
                    pygame.draw.polygon(
                        self.screen, COLOR_STAIRS,
                        [(center[0], center[1] - 10), (center[0] + 10, center[1]),
                         (center[0], center[1] + 10), (center[0] - 10, center[1])],
                    )
                else:
                    floor_color = COLOR_FLOOR_ALT if (map_x + map_y) % 2 else COLOR_FLOOR
                    pygame.draw.rect(self.screen, floor_color, rect)

        for enemy in self.enemies + self.dead_enemies:
            if enemy.alive and camera_x <= enemy.x < camera_x + VIEW_COLUMNS and camera_y <= enemy.y < camera_y + VIEW_ROWS:
                center = ((enemy.x - camera_x) * TILE_SIZE + TILE_SIZE // 2,
                          (enemy.y - camera_y) * TILE_SIZE + TILE_SIZE // 2)
                if isinstance(enemy, Boss) and self.player is not None:
                    draw_boss_telegraph(
                        self.screen,
                        enemy,
                        self.player,
                        self.dungeon,
                        (camera_x * TILE_SIZE, camera_y * TILE_SIZE),
                        self.boss_clock,
                        self.options.colorblind_mode,
                    )
                enemy.draw(self.screen, center, self.boss_clock)
            elif not enemy.alive and camera_x <= enemy.x < camera_x + VIEW_COLUMNS and camera_y <= enemy.y < camera_y + VIEW_ROWS:
                center = ((enemy.x - camera_x) * TILE_SIZE + TILE_SIZE // 2,
                          (enemy.y - camera_y) * TILE_SIZE + TILE_SIZE // 2)
                enemy.draw(self.screen, center, self.boss_clock)
        player_center = ((self.player.x - camera_x) * TILE_SIZE + TILE_SIZE // 2,
                         (self.player.y - camera_y) * TILE_SIZE + TILE_SIZE // 2)
        # Vẽ bóng và nhân vật sau bản đồ để bóng không bị các ô sàn che khuất.
        self.player.draw(self.screen, player_center)

        camera = (camera_x * TILE_SIZE, camera_y * TILE_SIZE)
        self.effects_surface.fill((0, 0, 0, 0))
        for projectile in self.projectiles:
            projectile.draw(self.effects_surface, camera)
        for projectile in self.boss_projectiles:
            projectile.draw(self.effects_surface, camera)
        for particle in self.particles:
            particle.draw(self.effects_surface, camera)
        if self.options.damage_numbers:
            for damage_text in self.damage_texts:
                damage_text.draw(self.effects_surface, camera)
        self.screen.blit(self.effects_surface, (0, 0))

        # Chớp sáng đầu kiếm/phép chỉ tồn tại trong khung hình bắn hiện tại.
        if self.muzzle_flash_position is not None:
            flash_center = (
                round(self.muzzle_flash_position[0] - camera[0]),
                round(self.muzzle_flash_position[1] - camera[1]),
            )
            pygame.draw.circle(self.screen, (95, 190, 255), flash_center, 17)
            pygame.draw.circle(self.screen, (205, 239, 255), flash_center, 10)
            pygame.draw.circle(self.screen, (255, 255, 255), flash_center, 5)
            self.muzzle_flash_position = None

        # HUD nằm trên cùng để hiệu ứng chiến đấu không che mất chỉ số.
        if self.player is not None and self.dungeon is not None:
            self.hud.colorblind_mode = self.options.colorblind_mode
            self.hud.draw(
                self.screen,
                self.player,
                self.dungeon,
                self.enemies,
                self.floor,
                self.message,
                self.message_timer,
            )
        if self.options.screen_shake and self.shake_offset != (0, 0):
            self.shake_surface.blit(self.screen, (0, 0))
            self.screen.fill(COLOR_BACKGROUND)
            self.screen.blit(self.shake_surface, self.shake_offset)
        if self.boss is not None and self.state not in {
            GameState.BOSS_INTRO,
            GameState.GAME_OVER,
        }:
            self.boss_health_bar.draw(self.screen, self.boss)
