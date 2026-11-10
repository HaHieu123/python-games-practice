"""Persistent achievement tracking for completed and ongoing runs."""

import json
import os
from pathlib import Path


ACHIEVEMENTS: dict[str, tuple[str, str]] = {
    "first_blood": ("First Blood", "Defeat your first enemy."),
    "boss_slayer": ("Boss Slayer", "Defeat any floor guardian."),
    "speedrun": ("Swift Descent", "Finish a run in under ten minutes."),
    "pacifist": ("Merciful", "Complete a run without defeating ordinary enemies."),
    "treasure_hunter": ("Treasure Hunter", "Earn at least 250 gold in one run."),
    "survivor": ("Unbroken", "Complete a floor without taking damage."),
    "archer": ("Storm of Bolts", "Land ten ranged hits in one run."),
    "collector": ("Well Prepared", "Buy five upgrades or potions."),
    "champion": ("Depths Champion", "Defeat the Demon Chicken."),
    "new_game_plus": ("One More Descent", "Unlock New Game+ by completing a run."),
}


def _default_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif os.name == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "FivefoldDepths" / "achievements.json"


class AchievementTracker:
    """Load, unlock, and persist the game's ten achievements."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _default_path()
        self.unlocked: set[str] = set()
        self.ng_plus_unlocked = False
        if self.path.is_file():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.unlocked = set(data.get("unlocked", [])) & ACHIEVEMENTS.keys()
                self.ng_plus_unlocked = bool(data.get("ng_plus_unlocked", False))
            except (OSError, json.JSONDecodeError, TypeError, AttributeError) as error:
                raise ValueError(f"Could not load achievements: {error}") from error

    def unlock(self, achievement_id: str) -> bool:
        """Unlock and save an achievement; return whether it was new."""
        if achievement_id not in ACHIEVEMENTS:
            raise KeyError(f"Unknown achievement: {achievement_id}")
        if achievement_id in self.unlocked:
            return False
        self.unlocked.add(achievement_id)
        if achievement_id == "new_game_plus":
            self.ng_plus_unlocked = True
        self.save()
        return True

    def save(self) -> None:
        """Atomically persist unlocks and the New Game+ flag."""
        temporary_path = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Ghi tệp tạm rồi thay thế để tránh lưu dở dang nếu chương trình bị ngắt.
            temporary_path.write_text(
                json.dumps(
                    {
                        "unlocked": sorted(self.unlocked),
                        "ng_plus_unlocked": self.ng_plus_unlocked,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            temporary_path.replace(self.path)
        except OSError as error:
            raise OSError(f"Could not save achievements: {error}") from error

    def all_unlocked(self) -> list[tuple[str, str, bool]]:
        return [
            (achievement_id, title, achievement_id in self.unlocked)
            for achievement_id, (title, _) in ACHIEVEMENTS.items()
        ]
