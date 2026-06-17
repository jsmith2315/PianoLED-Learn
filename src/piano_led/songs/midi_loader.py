"""Load MIDI files into playback events plus hand-setup track/channel summaries."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path

from piano_led.core.models import LoadedMidiSong, NoteEvent, TimedMidiEvent


@dataclass(frozen=True)
class MidiSongSummary:
    """Available track and channel info for manual hand assignment."""

    relative_path: str
    display_title: str
    track_indices: list[int] = field(default_factory=list)
    channels: list[int] = field(default_factory=list)


class MidiSongLoader:
    """Parse one MIDI file into playback-ready song data and summaries."""

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

        midi_file = self._load_midi_file(midi_path, error_label="load")
        tempo_changes = self._tempo_changes(midi_file)
        events: list[TimedMidiEvent] = []
        duration_seconds = 0.0

        for track_index, track in enumerate(midi_file.tracks):
            absolute_ticks = 0
            for message in track:
                absolute_ticks += int(message.time)
                absolute_seconds = self._ticks_to_seconds(absolute_ticks, tempo_changes, midi_file.ticks_per_beat)
                if getattr(message, "is_meta", False):
                    continue

                duration_seconds = max(duration_seconds, absolute_seconds)
                if message.type == "note_on" and message.velocity > 0:
                    events.append(
                        TimedMidiEvent(
                            time_seconds=absolute_seconds,
                            event=NoteEvent.note_on(message.note, message.velocity, "playback"),
                            track_index=track_index,
                            channel=getattr(message, "channel", None),
                        )
                    )
                elif message.type == "note_off" or (message.type == "note_on" and message.velocity == 0):
                    events.append(
                        TimedMidiEvent(
                            time_seconds=absolute_seconds,
                            event=NoteEvent.note_off(message.note, "playback"),
                            track_index=track_index,
                            channel=getattr(message, "channel", None),
                        )
                    )

        events.sort(key=lambda item: (item.time_seconds, 0 if item.event.event_type == "note_off" else 1))
        return LoadedMidiSong(
            relative_path=relative_path,
            display_title=display_title,
            duration_seconds=duration_seconds,
            events=events,
        )

    def summarize(self, midi_path: Path, relative_path: str, display_title: str) -> MidiSongSummary:
        """Inspect one MIDI file and return the track/channel choices for the UI."""

        midi_file = self._load_midi_file(midi_path, error_label="inspect")
        track_indices: list[int] = []
        channels: set[int] = set()

        for track_index, track in enumerate(midi_file.tracks):
            saw_note_message = False
            for message in track:
                if getattr(message, "is_meta", False):
                    continue
                if message.type in {"note_on", "note_off"}:
                    saw_note_message = True
                    if hasattr(message, "channel"):
                        channels.add(int(message.channel))
            if saw_note_message:
                track_indices.append(track_index)

        return MidiSongSummary(
            relative_path=relative_path,
            display_title=display_title,
            track_indices=track_indices,
            channels=sorted(channels),
        )

    def _load_midi_file(self, midi_path: Path, error_label: str):
        """Open one MIDI file and raise a readable RuntimeError on failure."""

        try:
            return self.mido.MidiFile(str(midi_path))
        except Exception as exc:
            raise RuntimeError(f"Unable to {error_label} MIDI file: {midi_path.name}") from exc

    def _tempo_changes(self, midi_file) -> list[tuple[int, int]]:
        """Collect global tempo changes as absolute ticks and tempo values."""

        tempo_changes: list[tuple[int, int]] = [(0, 500000)]
        for track in midi_file.tracks:
            absolute_ticks = 0
            for message in track:
                absolute_ticks += int(message.time)
                if getattr(message, "is_meta", False) and message.type == "set_tempo":
                    tempo_changes.append((absolute_ticks, int(message.tempo)))
        tempo_changes.sort(key=lambda item: item[0])
        return tempo_changes

    def _ticks_to_seconds(self, target_tick: int, tempo_changes: list[tuple[int, int]], ticks_per_beat: int) -> float:
        """Convert absolute ticks to seconds using the MIDI tempo timeline."""

        elapsed_seconds = 0.0
        current_tick = 0
        current_tempo = tempo_changes[0][1]

        for change_tick, next_tempo in tempo_changes[1:]:
            if change_tick >= target_tick:
                break
            delta_ticks = change_tick - current_tick
            elapsed_seconds += float(self.mido.tick2second(delta_ticks, ticks_per_beat, current_tempo))
            current_tick = change_tick
            current_tempo = next_tempo

        elapsed_seconds += float(self.mido.tick2second(target_tick - current_tick, ticks_per_beat, current_tempo))
        return elapsed_seconds
