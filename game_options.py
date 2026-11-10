"""Persistent accessibility and presentation settings."""

import json
import os
from pathlib import Path


def _default_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif os.name == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "FivefoldDepths" / "options.json"


class GameOptions:
    """Load, mutate, and save animation and display preferences."""

    SPEEDS = (0.75, 1.0, 1.25)

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _default_path()
        self.animation_speed = 1.0
        self.screen_shake = True
        self.damage_numbers = True
        self.colorblind_mode = False
        if self.path.is_file():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                speed = float(data.get("animation_speed", 1.0))
                self.animation_speed = min(self.SPEEDS, key=lambda option: abs(option - speed))
                self.screen_shake = bool(data.get("screen_shake", True))
                self.damage_numbers = bool(data.get("damage_numbers", True))
                self.colorblind_mode = bool(data.get("colorblind_mode", False))
            except (OSError, ValueError, TypeError) as error:
                raise ValueError(f"Could not load game options: {error}") from error

    def cycle_animation_speed(self) -> None:
        index = self.SPEEDS.index(self.animation_speed)
        self.animation_speed = self.SPEEDS[(index + 1) % len(self.SPEEDS)]
        self.save()

    def toggle(self, option: str) -> None:
        if option not in {"screen_shake", "damage_numbers", "colorblind_mode"}:
            raise KeyError(f"Unknown option: {option}")
        setattr(self, option, not getattr(self, option))
        self.save()

    def save(self) -> None:
        temporary_path = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path.write_text(
                json.dumps(
                    {
                        "animation_speed": self.animation_speed,
                        "screen_shake": self.screen_shake,
                        "damage_numbers": self.damage_numbers,
                        "colorblind_mode": self.colorblind_mode,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            temporary_path.replace(self.path)
        except OSError as error:
            raise OSError(f"Could not save game options: {error}") from error
