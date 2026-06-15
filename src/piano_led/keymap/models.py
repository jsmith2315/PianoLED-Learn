from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Keymap:
    note_to_led: dict[int, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, dict[str, int]]:
        return {"note_to_led": {str(note): led for note, led in self.note_to_led.items()}}

    @classmethod
    def from_dict(cls, payload: dict) -> "Keymap":
        data = payload.get("note_to_led", {})
        return cls(note_to_led={int(note): int(led) for note, led in data.items()})

