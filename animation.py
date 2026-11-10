"""Delta-time animation state machine for procedural dungeon sprites."""

from collections.abc import Callable
from dataclasses import dataclass

import pygame


@dataclass(frozen=True)
class AnimationSpec:
    """Timing and playback policy for one animation state."""

    frames: int
    fps: float
    loop: bool


class Animation:
    """Priority-aware animation controller with one-shot completion callbacks."""

    SPECS = {
        "idle": AnimationSpec(2, 4.0, True),
        "walk": AnimationSpec(4, 8.0, True),
        "attack": AnimationSpec(3, 12.0, False),
        "hurt": AnimationSpec(1, 12.0, False),
        "death": AnimationSpec(4, 8.0, False),
    }
    # Ưu tiên cao hơn ngăn trạng thái bị đau/chết bị hoạt ảnh đi bộ ghi đè.
    PRIORITY = {"idle": 0, "walk": 1, "attack": 2, "hurt": 3, "death": 4}

    def __init__(
        self,
        on_finish: Callable[[str], None] | None = None,
        speed_scale: float = 1.0,
    ) -> None:
        self.state = "idle"
        self.facing = "down"
        self.frame = 0
        self.elapsed = 0.0
        self.speed_scale = max(0.1, speed_scale)
        self.on_finish = on_finish
        self.finished = False

    @property
    def frame_name(self) -> str:
        """Return a spritesheet-compatible name, e.g. ``walk_left_2``."""
        direction = self.facing if self.state in {"idle", "walk"} else ""
        parts = [self.state]
        if direction:
            parts.append(direction)
        parts.append(str(self.frame))
        return "_".join(parts)

    def set_facing(self, facing: str) -> None:
        if facing in {"up", "down", "left", "right"}:
            self.facing = facing

    def set_state(
        self,
        state: str,
        *,
        force: bool = False,
        on_finish: Callable[[str], None] | None = None,
    ) -> bool:
        """Switch state if its priority permits; return whether it changed."""
        if state not in self.SPECS:
            raise ValueError(f"Unknown animation state: {state}")
        if state == self.state and not force:
            if on_finish is not None:
                self.on_finish = on_finish
            return False
        if not force and self.PRIORITY[state] < self.PRIORITY[self.state] and not self.finished:
            return False
        self.state = state
        self.frame = 0
        self.elapsed = 0.0
        self.finished = False
        self.on_finish = on_finish
        return True

    def update(self, dt: float) -> None:
        """Advance frames using seconds; invoke callbacks once on completion."""
        dt = max(0.0, dt) * self.speed_scale
        if self.finished:
            return
        spec = self.SPECS[self.state]
        self.elapsed += dt
        frame_duration = 1.0 / max(0.01, spec.fps)
        # Dùng vòng lặp để không bỏ mất khung hình khi dt lớn hơn thời lượng một frame.
        while self.elapsed >= frame_duration and not self.finished:
            self.elapsed -= frame_duration
            if self.frame + 1 < spec.frames:
                self.frame += 1
            elif spec.loop:
                self.frame = 0
            else:
                self.frame = spec.frames - 1
                self.finished = True
                if self.on_finish is not None:
                    callback = self.on_finish
                    self.on_finish = None
                    callback(self.state)

    def draw(self, surface: pygame.Surface, draw_frame: Callable[[pygame.Surface, int, str], None]) -> None:
        """Delegate procedural frame rendering to the owning entity."""
        draw_frame(surface, self.frame, self.facing)

    @staticmethod
    def flipped_facing(facing: str) -> str:
        """Return the equivalent horizontal flip for spritesheet workflows."""
        return {"left": "right", "right": "left"}.get(facing, facing)
