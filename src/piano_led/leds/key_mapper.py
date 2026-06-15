from __future__ import annotations

from piano_led.keymap.models import Keymap


class KeyMapper:
    def __init__(self, keymap: Keymap) -> None:
        self.keymap = keymap

    def led_for_note(self, note: int) -> int | None:
        return self.keymap.note_to_led.get(note)

