from __future__ import annotations

from piano_led.core.notes import HIGHEST_PIANO_NOTE, LOWEST_PIANO_NOTE
from piano_led.keymap.models import Keymap


class KeymapGenerator:
    def generate(self, total_leds: int, first_led: int, direction: str) -> Keymap:
        note_count = HIGHEST_PIANO_NOTE - LOWEST_PIANO_NOTE + 1
        if total_leds <= 0:
            raise ValueError("total_leds must be positive")
        if direction not in {"left_to_right", "right_to_left"}:
            raise ValueError("direction must be left_to_right or right_to_left")

        end_led = total_leds - 1 if direction == "left_to_right" else 0
        span = end_led - first_led
        mapping: dict[int, int] = {}

        for offset, note in enumerate(range(LOWEST_PIANO_NOTE, HIGHEST_PIANO_NOTE + 1)):
            ratio = offset / (note_count - 1)
            led_index = round(first_led + (span * ratio))
            mapping[note] = led_index

        return Keymap(note_to_led=mapping)

