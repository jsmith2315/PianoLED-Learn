from __future__ import annotations

from dataclasses import dataclass, field

from piano_led.keymap.models import Keymap


@dataclass
class CalibrationSession:
    keymap: Keymap
    note_order: list[int]
    selected_note: int | None = None
    completed_notes: list[int] = field(default_factory=list)

    def select_key(self, note: int) -> int:
        if note not in self.keymap.note_to_led:
            raise KeyError(f"Note {note} is not in the current keymap")
        self.selected_note = note
        return self.keymap.note_to_led[note]

    def shift(self, delta: int) -> int:
        if self.selected_note is None:
            raise RuntimeError("No note selected for calibration")
        self.keymap.note_to_led[self.selected_note] += delta
        return self.keymap.note_to_led[self.selected_note]

    def confirm_key(self, note: int) -> bool:
        if self.selected_note != note:
            return False
        if note not in self.completed_notes:
            self.completed_notes.append(note)
        self.selected_note = None
        return True

    def to_dict(self) -> dict:
        active_led = None
        if self.selected_note is not None:
            active_led = self.keymap.note_to_led[self.selected_note]
        return {
            "selected_note": self.selected_note,
            "active_led": active_led,
            "completed_notes": self.completed_notes,
            "remaining_notes": [note for note in self.note_order if note not in self.completed_notes],
        }

