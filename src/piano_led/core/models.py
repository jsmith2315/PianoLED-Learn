"""Small shared dataclasses used across the runtime."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NoteEvent:
    """Normalized note event independent of any specific MIDI library."""
    event_type: str
    note: int
    velocity: int
    source: str

    @classmethod
    def note_on(cls, note: int, velocity: int, source: str) -> "NoteEvent":
        return cls(event_type="note_on", note=note, velocity=velocity, source=source)

    @classmethod
    def note_off(cls, note: int, source: str) -> "NoteEvent":
        return cls(event_type="note_off", note=note, velocity=0, source=source)
