"""Load MIDI files into absolute-timed note events for playback."""

from __future__ import annotations

import importlib
from pathlib import Path

from piano_led.core.models import LoadedMidiSong, NoteEvent, TimedMidiEvent


class MidiSongLoader:
    """Parse one MIDI file into a playback-ready song model."""

    def __init__(self, mido_module=None) -> None:
        self._mido = mido_module

    @property
    def mido(self):
        """Lazily import the configured MIDI module."""

        if self._mido is None:
            self._mido = importlib.import_module("mido")
        return self._mido

    def load(self, midi_path: Path, relative_path: str, display_title: str) -> LoadedMidiSong:
        """Read one MIDI file and flatten note timing into absolute seconds."""

        try:
            midi_file = self.mido.MidiFile(str(midi_path))
        except Exception as exc:
            raise RuntimeError(f"Unable to load MIDI file: {midi_path.name}") from exc

        absolute_time = 0.0
        events: list[TimedMidiEvent] = []
        for message in midi_file:
            absolute_time += float(message.time)
            if getattr(message, "is_meta", False):
                continue

            if message.type == "note_on" and message.velocity > 0:
                events.append(
                    TimedMidiEvent(
                        time_seconds=absolute_time,
                        event=NoteEvent.note_on(message.note, message.velocity, "playback"),
                    )
                )
            elif message.type == "note_off" or (message.type == "note_on" and message.velocity == 0):
                events.append(
                    TimedMidiEvent(
                        time_seconds=absolute_time,
                        event=NoteEvent.note_off(message.note, "playback"),
                    )
                )

        return LoadedMidiSong(
            relative_path=relative_path,
            display_title=display_title,
            duration_seconds=absolute_time,
            events=events,
        )
