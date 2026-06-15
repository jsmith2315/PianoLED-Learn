"""Helper for generating and saving keymap files from the command line."""

from __future__ import annotations

import json
from pathlib import Path

from piano_led.keymap.generator import KeymapGenerator


def generate_keymap_file(path: Path, total_leds: int, first_led: int, direction: str) -> None:
    """Generate a keymap and save it to disk as JSON."""

    keymap = KeymapGenerator().generate(total_leds=total_leds, first_led=first_led, direction=direction)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(keymap.to_dict(), handle, indent=2)
