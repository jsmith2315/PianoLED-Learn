"""JSON-backed settings models for LED and MIDI configuration."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class LedSettings:
    """LED-strip parameters and backend selection."""
    total_leds: int = 176
    leds_per_meter: int = 144
    note_color: str = "#00b894"
    black_key_color: str = "#0984e3"
    use_black_key_color: bool = True
    strip_direction: str = "left_to_right"
    default_first_led: int = 0
    backend: str = "fake"
    gpio_pin: int = 18
    brightness: int = 128
    dma_channel: int = 10
    pwm_frequency_hz: int = 800000
    invert_signal: bool = False
    channel: int = 0


@dataclass
class MidiSettings:
    """MIDI backend selection and configured port names."""
    backend: str = "fake"
    input_port_name: str = ""
    output_port_name: str = ""


@dataclass
class AppSettings:
    """Top-level settings document stored on disk."""
    led: LedSettings = field(default_factory=LedSettings)
    midi: MidiSettings = field(default_factory=MidiSettings)
    selected_keymap: str = "default_88.json"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "AppSettings":
        led = LedSettings(**payload.get("led", {}))
        midi = MidiSettings(**payload.get("midi", {}))
        return cls(led=led, midi=midi, selected_keymap=payload.get("selected_keymap", "default_88.json"))


class SettingsStore:
    """Load and save ``AppSettings`` as JSON."""
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> AppSettings:
        if not self.path.exists():
            settings = AppSettings()
            self.save(settings)
            return settings

        with self.path.open("r", encoding="utf-8") as handle:
            return AppSettings.from_dict(json.load(handle))

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(settings.to_dict(), handle, indent=2)
