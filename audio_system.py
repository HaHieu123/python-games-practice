"""Procedurally synthesized background music and sound effects."""

from __future__ import annotations

from array import array
import logging
import math

import pygame

LOGGER = logging.getLogger(__name__)
SAMPLE_RATE = 22050


class AudioSystem:
    """Own Pygame mixer playback and generated audio samples."""

    def __init__(self) -> None:
        self.available = False
        self.volume = 0.7
        self.music_channel: pygame.mixer.Channel | None = None
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if pygame.mixer.get_init() != (SAMPLE_RATE, -16, 1):
                pygame.mixer.quit()
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=512)
        except pygame.error as error:
            LOGGER.warning("Audio is unavailable: %s", error)
            return

        pygame.mixer.set_num_channels(max(8, pygame.mixer.get_num_channels()))
        pygame.mixer.set_reserved(1)
        self.available = True
        self.music_channel = pygame.mixer.Channel(0)
        self.sounds = {
            "attack": self._tone(((210, 0.12), (145, 0.09)), volume=0.36),
            "enemy_attack": self._tone(((115, 0.12), (78, 0.12)), volume=0.34),
            "defeat": self._tone(((420, 0.15), (315, 0.18), (210, 0.25)), volume=0.32),
            "purchase": self._tone(((440, 0.11), (660, 0.12), (880, 0.16)), volume=0.25),
            "stairs": self._tone(((294, 0.2), (392, 0.2), (587, 0.32)), volume=0.28),
            "error": self._tone(((150, 0.2), (115, 0.18)), volume=0.24),
            "victory": self._tone(((392, 0.16), (494, 0.16), (587, 0.2), (784, 0.42)), volume=0.28),
        }
        self.music = self._make_music()
        self.boss_music = self._make_boss_music()

    def start_music(self) -> None:
        """Start the generated atmospheric loop if audio is available."""
        if self.available and self.music_channel is not None:
            self.music_channel.play(self.music, loops=-1)
            self.music_channel.set_volume(self.volume)

    def start_boss_music(self) -> None:
        """Switch to a procedurally generated low, pulsing boss theme."""
        if self.available and self.music_channel is not None:
            self.music_channel.play(self.boss_music, loops=-1)
            self.music_channel.set_volume(self.volume)

    def stop(self) -> None:
        """Stop all mixer playback owned by this system."""
        if self.available and self.music_channel is not None:
            self.music_channel.stop()

    def set_volume(self, value: float) -> None:
        """Set the shared volume for background music and future sound effects."""
        self.volume = max(0.0, min(1.0, value))
        if self.available and self.music_channel is not None:
            self.music_channel.set_volume(self.volume)

    def play(self, name: str) -> None:
        """Play a named sound effect when the mixer is available."""
        sound = self.sounds.get(name)
        if sound is not None:
            sound.set_volume(self.volume)
            sound.play()

    def _tone(
        self,
        notes: tuple[tuple[float, float], ...],
        *,
        volume: float,
    ) -> pygame.mixer.Sound:
        """Synthesize a sequence of soft, fading sine tones."""
        samples = array("h")
        for frequency, duration in notes:
            count = max(1, round(SAMPLE_RATE * duration))
            for index in range(count):
                progress = index / count
                envelope = min(1.0, progress * 12) * (1.0 - progress) ** 0.7
                value = math.sin(2 * math.pi * frequency * index / SAMPLE_RATE)
                samples.append(round(32767 * volume * envelope * value))
            samples.extend([0] * round(SAMPLE_RATE * 0.025))
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def _make_music(self) -> pygame.mixer.Sound:
        """Create a gentle eight-second minor-key arpeggio loop."""
        duration = 8.0
        total_samples = round(SAMPLE_RATE * duration)
        samples = array("h")
        melody = (110.0, 164.81, 220.0, 164.81, 130.81, 196.0, 261.63, 196.0)
        beat = SAMPLE_RATE
        for index in range(total_samples):
            time = index / SAMPLE_RATE
            note_index = (index // beat) % len(melody)
            local_time = (index % beat) / SAMPLE_RATE
            note_envelope = min(1.0, local_time * 7) * max(0.0, 1.0 - local_time / 1.15)
            melody_sample = math.sin(2 * math.pi * melody[note_index] * time)
            overtone = math.sin(2 * math.pi * melody[note_index] * 1.5 * time) * 0.18
            bass_frequency = melody[(note_index // 4) * 4] / 2
            bass_sample = math.sin(2 * math.pi * bass_frequency * time) * 0.3
            sample = (melody_sample + overtone) * note_envelope * 0.09 + bass_sample * 0.045
            samples.append(max(-32767, min(32767, round(32767 * sample))))
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def _make_boss_music(self) -> pygame.mixer.Sound:
        """Synthesize a tense low-register four-note boss loop."""
        duration = 4.0
        samples = array("h")
        notes = (55.0, 65.41, 49.0, 73.42)
        for index in range(round(SAMPLE_RATE * duration)):
            time = index / SAMPLE_RATE
            note_index = int(time) % len(notes)
            pulse = 0.55 + 0.45 * math.sin(time * math.tau * 2)
            fundamental = math.sin(math.tau * notes[note_index] * time)
            fifth = math.sin(math.tau * notes[note_index] * 1.5 * time) * 0.24
            samples.append(round(32767 * (fundamental + fifth) * pulse * 0.12))
        return pygame.mixer.Sound(buffer=samples.tobytes())
