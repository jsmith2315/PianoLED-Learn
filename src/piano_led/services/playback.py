"""Background MIDI playback service for the first Practice page slice."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

from piano_led.core.models import LoadedMidiSong, NoteEvent, PlaybackState
from piano_led.midi.output import MidiOutputPort
from piano_led.songs.midi_loader import MidiSongLoader


class PlaybackService:
    """Play one selected MIDI song at a time and expose serializable state."""

    def __init__(self, midi_output: MidiOutputPort | None = None, midi_loader: MidiSongLoader | None = None) -> None:
        self.midi_output = midi_output
        self.midi_loader = midi_loader or MidiSongLoader()
        self.state = PlaybackState()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._active_notes: set[int] = set()
        self._emit_note_event: Callable[[NoteEvent], None] | None = None
        self._clear_leds: Callable[[], None] | None = None

    def play_song(
        self,
        midi_path: Path,
        relative_path: str,
        display_title: str,
        emit_note_event: Callable[[NoteEvent], None],
        clear_leds: Callable[[], None],
    ) -> dict:
        """Load and play one song from the beginning in a background thread."""

        with self._lock:
            if self.state.status == "playing":
                return self.state.to_dict()

        song = self.midi_loader.load(midi_path, relative_path, display_title)
        midi_output_enabled = self._open_midi_output()

        with self._lock:
            self._emit_note_event = emit_note_event
            self._clear_leds = clear_leds
            self._stop_event.clear()
            self._active_notes.clear()
            self.state = PlaybackState(
                status="playing",
                selected_song_path=relative_path,
                song_title=display_title,
                duration_seconds=song.duration_seconds,
                elapsed_seconds=0.0,
                active_notes=[],
                midi_output_enabled=midi_output_enabled,
                error=None,
            )
            self._thread = threading.Thread(target=self._run_song, args=(song,), daemon=True)
            self._thread.start()
            return self.state.to_dict()

    def stop(self) -> dict:
        """Request playback stop and wait briefly for cleanup to complete."""

        thread: threading.Thread | None = None
        with self._lock:
            self._stop_event.set()
            thread = self._thread

        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)

        if thread is None or not thread.is_alive():
            self._finish_playback(stopped_early=True)
        return self.get_state()

    def get_state(self) -> dict:
        """Return the current playback state as a plain dictionary."""

        with self._lock:
            return self.state.to_dict()

    def _open_midi_output(self) -> bool:
        """Open MIDI output when available, but allow LED-only playback on failure."""

        if self.midi_output is None:
            return False
        try:
            self.midi_output.open()
        except Exception:
            return False
        return True

    def _run_song(self, song: LoadedMidiSong) -> None:
        """Schedule playback against a monotonic clock until stop or completion."""

        start_time = time.monotonic()
        try:
            for timed_event in song.events:
                if self._stop_event.is_set():
                    break
                while not self._stop_event.is_set():
                    elapsed = time.monotonic() - start_time
                    if elapsed >= timed_event.time_seconds:
                        break
                    time.sleep(0.002)
                if self._stop_event.is_set():
                    break
                self._emit_event(timed_event.event)
                with self._lock:
                    self.state.elapsed_seconds = min(timed_event.time_seconds, song.duration_seconds)
                    self.state.active_notes = sorted(self._active_notes)
        except Exception as exc:
            with self._lock:
                self.state.error = str(exc)
        finally:
            self._finish_playback(stopped_early=self._stop_event.is_set())

    def _emit_event(self, event: NoteEvent) -> None:
        """Forward one playback event to the runtime and optional MIDI output."""

        if event.event_type == "note_on":
            self._active_notes.add(event.note)
        elif event.event_type == "note_off":
            self._active_notes.discard(event.note)

        if self._emit_note_event is not None:
            self._emit_note_event(event)

        if self.midi_output is not None and self.state.midi_output_enabled:
            try:
                self.midi_output.send(event)
            except Exception:
                with self._lock:
                    self.state.midi_output_enabled = False

    def _flush_active_notes(self) -> None:
        """Send note-off events for every currently active playback note."""

        for note in sorted(self._active_notes):
            self._emit_event(NoteEvent.note_off(note, "playback"))
        self._active_notes.clear()

    def _finish_playback(self, stopped_early: bool) -> None:
        """Clear notes, clear LEDs, and return the playback state to stopped."""

        with self._lock:
            if self.state.status == "stopped" and not self._active_notes and self._thread is None:
                return

        self._flush_active_notes()
        if self._clear_leds is not None:
            self._clear_leds()

        with self._lock:
            if stopped_early:
                self.state.elapsed_seconds = 0.0
            else:
                self.state.elapsed_seconds = self.state.duration_seconds
            self.state.status = "stopped"
            self.state.active_notes = []
            self._thread = None
            self._stop_event.clear()
