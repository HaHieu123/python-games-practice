# The Fivefold Depths

A six-floor, turn-based dungeon crawler built with Pygame CE. All characters and
combat effects are rendered with `pygame.draw`; the game does not require image
or audio assets.

## Run

From the folder containing `dungeon_crawler/`:

```powershell
python -m pip install -r dungeon_crawler/requirements.txt
python -m dungeon_crawler.main
```

You can also run `python main.py` from inside the `dungeon_crawler/` folder.

## Build a standalone Windows executable

From inside the `dungeon_crawler/` folder, install the build dependencies and
run the PowerShell build script:

```powershell
python -m pip install -r requirements-build.txt
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

The one-file executable is written to `..\dist\TheFivefoldDepths.exe`.
If an `assets/` directory is present, its contents are bundled with the build.
The current soundtrack and sound effects are synthesized at runtime, so no
external audio files are required.

## Current controls

- **WASD** or **arrow keys**: move / attack an adjacent enemy
- **F**: fire a homing bolt at the nearest enemy within range
- **I**: open the inventory screen
- **Esc**: pause/resume, or return from settings
- **Left / right arrows**: adjust master volume in Settings; use **1–4** to
  cycle animation speed and toggle screen shake, damage numbers, and the
  colorblind palette
- **1 / 2 / 3**: buy the corresponding shop offer between floors
- **Enter** or **Esc**: leave the shop and descend
- **Mouse**: click menus and drag the Settings volume slider

## Animation approach

The current implementation uses **procedural drawing** (Option B). This is the
most approachable starting point: no art program, image slicing, or asset
loading is required, and the animation state/timing behavior remains easy to
inspect in Python. `animation.py` provides four-direction walk and idle states,
one-shot attack/hurt/death states, frame timing, and completion callbacks.

To replace procedural art with sprites later, create files using this naming
pattern, for example:

```text
assets/
  sprites/
    player_idle_down_0.png
    player_idle_down_1.png
    player_walk_down_0.png
    player_walk_down_1.png
    player_walk_down_2.png
    player_walk_down_3.png
    player_attack_down_0.png
    slime_walk_left_0.png
```

Use the pattern `<character>_<state>_<direction>_<frame>.png`; provide four
walk frames per direction, two idle frames, three attack frames, and four
death frames. The animation controller exposes matching frame names. A
spritesheet loader is not included yet; these files can be introduced later
without changing the game's animation timing/state rules.

## Boss encounters

Guardians appear on floors 2, 4, and 6. A red (or yellow in colorblind mode)
tile preview shows their telegraphed attack area; move before the boss resolves
the attack. The final boss's Egg Bomb has a two-turn warning, and walls block
its blast.

- **Floor 2 — Giant Slime King:** the jump slam threatens a 3×3 area; move out
  of the highlighted tiles. It can summon slimes and fire acid. Below 30% HP it
  enrages and attacks sooner.
- **Floor 4 — Skeleton Lord:** summons skeletons, fires a five-bone spread, or
  charges along a line. At half HP it gains a two-turn shield and can teleport;
  wait out the shield and use ranged attacks while it repositions.
- **Floor 6 — Demon Chicken:** uses a directional fire cone and feather
  volleys, then becomes immune to melee briefly while airborne. In its final
  phase it berserks, summons chicks, and dives. Break line of sight behind a
  wall to avoid Egg Bomb damage.

Boss music is generated as simple tones at runtime, so no music files are
needed. Checkpoints are saved before each boss floor. Defeating the final
guardian completes the run and unlocks New Game+; that mode increases enemy
health/attack and improves gold rewards.

## Completion and accessibility

Ten achievements are stored as JSON in the user's application-data directory.
The run summary reports elapsed time, kills, and damage dealt/taken. The Settings
screen includes animation speed, screen-shake, damage-number, and colorblind
palette options; these preferences are also persisted as JSON.

## Frame update and draw order

The main loop caps `dt` at 0.05 seconds and targets 60 FPS. Gameplay updates
player regeneration/animation, projectile collisions, boss projectiles, enemy
animations, then particles and floating text. Rendering follows this order:

```python
dt = min(clock.tick(FPS) / 1000.0, 0.05)
game._handle_events()
game._update(dt)
game._draw()
pygame.display.flip()
```

1. Dungeon map and telegraph tiles
2. Enemies and bosses
3. Player (glow, shadow, then character layers)
4. Projectiles, particles, and floating damage text
5. HUD, minimap, and boss health bar

The game also includes connected procedural floors, turn-based combat, passive
health regeneration and potions, a shop between floors, synthesized music and
sound effects, inventory overview, pause/settings screens, and persistent run
saves. Inventory equipment slots are display-only; item collection/equipping
is not implemented.
