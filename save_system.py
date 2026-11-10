"""JSON save/load helpers using the current user's application-data folder."""

import json
import os
from pathlib import Path
from typing import Any

from .settings import SAVE_VERSION

SAVE_DIRECTORY_NAME = "FivefoldDepths"
SAVE_FILE_NAME = "save.json"


class SaveError(Exception):
    """Raised when a save cannot be read, validated, or written."""


def get_save_path() -> Path:
    """Return the platform-appropriate path for the game's JSON save file."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif os.name == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / SAVE_DIRECTORY_NAME / SAVE_FILE_NAME


def has_save(path: Path | None = None) -> bool:
    """Return whether a save file exists at the provided or default path."""
    return (path or get_save_path()).is_file()


def save_game(data: dict[str, Any], path: Path | None = None) -> Path:
    """Write a versioned save atomically and return its path."""
    save_path = path or get_save_path()
    temporary_path = save_path.with_suffix(save_path.suffix + ".tmp")
    payload = {"version": SAVE_VERSION, "game": data}
    try:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with temporary_path.open("w", encoding="utf-8") as save_file:
            json.dump(payload, save_file, indent=2)
            save_file.flush()
            os.fsync(save_file.fileno())
        temporary_path.replace(save_path)
    except (OSError, TypeError, ValueError) as error:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise SaveError(f"Could not write save file: {error}") from error
    return save_path


def load_game(path: Path | None = None) -> dict[str, Any] | None:
    """Load and validate a save; return ``None`` if no save exists.

    Malformed JSON, incompatible versions, and invalid save shapes raise
    ``SaveError`` so the UI can report the problem rather than silently
    starting from a misleading partial save.
    """
    save_path = path or get_save_path()
    if not save_path.exists():
        return None
    try:
        with save_path.open("r", encoding="utf-8") as save_file:
            payload = json.load(save_file)
        if not isinstance(payload, dict):
            raise ValueError("Top-level save data must be an object.")
        if payload.get("version") != SAVE_VERSION:
            raise ValueError(f"Unsupported save version: {payload.get('version')!r}.")
        game_data = payload.get("game")
        if not isinstance(game_data, dict):
            raise ValueError("Save is missing its game data object.")
        required = {"floor", "player", "dungeon", "enemies"}
        if not required.issubset(game_data):
            raise ValueError("Save is missing required game data.")
        if not isinstance(game_data["player"], dict) or not isinstance(game_data["dungeon"], dict):
            raise ValueError("Save has invalid player or dungeon data.")
        if not isinstance(game_data["enemies"], list):
            raise ValueError("Save has invalid enemy data.")
        return game_data
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError) as error:
        raise SaveError(f"Could not load save file: {error}") from error
