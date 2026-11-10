"""Application entry point."""

import sys
from pathlib import Path

if __package__:
    from .game import Game
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from dungeon_crawler.game import Game


def main() -> None:
    """Create and run the game."""
    Game().run()


if __name__ == "__main__":
    main()
