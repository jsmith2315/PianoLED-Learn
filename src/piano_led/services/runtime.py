"""Long-lived runtime behavior for note lighting, calibration, playback, and state."""

from __future__ import annotations

from piano_led.config.settings import AppSettings, SettingsStore
from piano_led.core.colors import hex_to_rgb
from piano_led.core.models import NoteEvent
from piano_led.core.notes import HIGHEST_PIANO_NOTE, LOWEST_PIANO_NOTE, is_black_key
from piano_led.keymap.calibrator import CalibrationSession
from piano_led.keymap.generator import KeymapGenerator
from piano_led.keymap.models import Keymap
from piano_led.keymap.storage import KeymapStore
from piano_led.leds.animations import chase_step
from piano_led.leds.driver_base import LedDriver
from piano_led.leds.key_mapper import KeyMapper
from piano_led.midi.input import MidiInputPort
from piano_led.midi.output import MidiOutputPort
from piano_led.services.playback import PlaybackService
from piano_led.services.state_store import StateStore
from piano_led.songs.hand_config import SongHandConfig, SongHandConfigStore
from piano_led.songs.library import SongLibrary


class PianoLedRuntime:
    """Coordinate note events, keymaps, LED output, and runtime state."""

    def __init__(
        self,
        settings: AppSettings,
        keymap: Keymap,
        led_driver: LedDriver,
        settings_store: SettingsStore | None = None,
        keymap_store: KeymapStore | None = None,
        state_store: StateStore | None = None,
        song_library: SongLibrary | None = None,
        midi_output: MidiOutputPort | None = None,
        song_hand_config_store: SongHandConfigStore | None = None,
    ) -> None:
        self.settings = settings
        self.keymap = keymap
        self.led_driver = led_driver
        self.settings_store = settings_store
        self.keymap_store = keymap_store
        self.state_store = state_store or StateStore()
        self.song_library = song_library
        self.midi_output = midi_output
        self.song_hand_config_store = song_hand_config_store
        self.playback = PlaybackService(midi_output=midi_output)
        self.playback_hand_mode = "both"
        self.selected_song_path: str | None = None
        self.song_snapshot = {
            "songs": [],
            "selected_song_path": None,
            "selected_song": None,
        }
        self.key_mapper = KeyMapper(keymap)
        self.active_notes: set[int] = set()
        self.last_note_event: dict | None = None
        self.calibration_session: CalibrationSession | None = None
        self.show_full_keyboard_preview_during_calibration = False
        self.full_map_preview_active = False
        self.awaiting_calibration_note = False
        self.chase_index = 0
        self.midi_input: MidiInputPort | None = None
        self._reload_song_snapshot()
        self.refresh_state()

    def describe(self) -> str:
        """Return a compact summary for logs, status commands, and services."""

        return (
            f"Piano LED runtime ready: leds={self.settings.led.total_leds}, "
            f"keymap_notes={len(self.keymap.note_to_led)}, "
            f"calibration_active={self.calibration_session is not None}, "
            f"led_backend={self.settings.led.backend}, "
            f"midi_backend={self.settings.midi.backend}, "
            f"midi_in={self.settings.midi.input_port_name or '<unset>'}"
        )

    def _cache_song_snapshot(self, songs: list[dict]) -> dict:
        """Cache songs plus a reconciled current selection."""

        selected_song = None
        if self.selected_song_path is not None:
            for song in songs:
                if song["relative_path"] == self.selected_song_path:
                    selected_song = song
                    break
            if selected_song is None:
                self.selected_song_path = None
        self.song_snapshot = {
            "songs": songs,
            "selected_song_path": self.selected_song_path,
            "selected_song": selected_song,
        }
        return self.song_snapshot

    def _reload_song_snapshot(self) -> dict:
        """Rescan the song library and refresh the cached selection snapshot."""

        songs = [] if self.song_library is None else self.song_library.list_songs()
        return self._cache_song_snapshot(songs)

    def list_songs(self) -> list[dict]:
        """Return the currently available MIDI songs."""

        snapshot = self._reload_song_snapshot()
        self.refresh_state()
        return snapshot["songs"]

    def get_selected_song(self) -> dict | None:
        """Return metadata for the currently selected song, if any."""

        snapshot = self._reload_song_snapshot()
        self.refresh_state()
        return snapshot["selected_song"]

    def get_song_selection_state(self) -> dict:
        """Return the available songs plus the current selection."""

        snapshot = self._reload_song_snapshot()
        self.refresh_state()
        return snapshot

    def select_song(self, relative_path: str) -> dict:
        """Select a MIDI file from the current song library."""

        snapshot = self._reload_song_snapshot()
        for song in snapshot["songs"]:
            if song["relative_path"] == relative_path:
                self.selected_song_path = relative_path
                snapshot = self._cache_song_snapshot(snapshot["songs"])
                self.refresh_state()
                return snapshot
        raise ValueError(f"Unknown song selection: {relative_path}")

    def handle_note_event(self, event: NoteEvent, hand: str = "unassigned") -> None:
        """Update LEDs and runtime state for one note event."""

        self.last_note_event = {
            "event_type": event.event_type,
            "note": event.note,
            "velocity": event.velocity,
            "source": event.source,
            "hand": hand,
        }
        if event.source != "playback" and self.playback.get_state()["status"] == "playing":
            self.refresh_state()
            return

        if event.event_type == "note_on" and self.calibration_session is not None and self.awaiting_calibration_note:
            self.capture_calibration_note(event.note)
            return

        if (
            event.event_type == "note_off"
            and self.calibration_session is not None
            and self.calibration_session.selected_note == event.note
        ):
            self.active_notes.discard(event.note)
            self.refresh_state()
            return

        led_index = self.key_mapper.led_for_note(event.note)
        if led_index is None:
            return

        if event.event_type == "note_on":
            color = self.note_color_for(event.note, hand=hand)
            self.led_driver.set_pixel(led_index, color)
            self.active_notes.add(event.note)
        elif event.event_type == "note_off":
            self.led_driver.set_pixel(led_index, (0, 0, 0))
            self.active_notes.discard(event.note)

        self.led_driver.show()
        self.refresh_state()

    def _in_led_range(self, led_index: int) -> bool:
        return 0 <= led_index < self.settings.led.total_leds

    def _render_full_keymap_to_strip(self) -> None:
        self.led_driver.clear()
        for note, led_index in self.keymap.note_to_led.items():
            if self._in_led_range(led_index):
                self.led_driver.set_pixel(led_index, self.note_color_for(note))
        self.led_driver.show()

    def preview_full_keymap(self) -> dict:
        """Render the current whole-keyboard keymap on the LED strip."""

        self.full_map_preview_active = True
        self._render_full_keymap_to_strip()
        self.refresh_state()
        return self.get_keymap_state()

    def clear_full_keymap_preview(self) -> dict:
        """Turn off any whole-keyboard preview currently shown on the strip."""

        self.full_map_preview_active = False
        self.clear_leds()
        self.refresh_state()
        return self.get_keymap_state()

    def shift_full_keymap_piano(self, direction: str) -> dict:
        """Shift every mapped LED by one step in physical piano direction."""

        if direction not in {"left", "right"}:
            raise ValueError(f"Unsupported piano direction: {direction}")

        if self.settings.led.strip_direction == "right_to_left":
            delta = 1 if direction == "left" else -1
        else:
            delta = -1 if direction == "left" else 1

        for note in list(self.keymap.note_to_led):
            self.keymap.note_to_led[note] += delta

        if self.keymap_store is not None:
            self.keymap_store.save(self.keymap)

        if self.full_map_preview_active or (
            self.calibration_session is not None
            and self.show_full_keyboard_preview_during_calibration
            and self.calibration_session.selected_note is None
        ):
            self._render_full_keymap_to_strip()

        self.refresh_state()
        return self.get_keymap_state()

    def note_color_for(self, note: int, hand: str = "unassigned") -> tuple[int, int, int]:
        """Return the configured note color for one piano note."""

        if hand == "left":
            if is_black_key(note):
                return hex_to_rgb(self.settings.led.left_hand_black_key_color)
            return hex_to_rgb(self.settings.led.left_hand_note_color)
        if hand == "right":
            if is_black_key(note):
                return hex_to_rgb(self.settings.led.right_hand_black_key_color)
            return hex_to_rgb(self.settings.led.right_hand_note_color)
        if self.settings.led.use_black_key_color and is_black_key(note):
            return hex_to_rgb(self.settings.led.black_key_color)
        return hex_to_rgb(self.settings.led.note_color)

    def clear_leds(self) -> None:
        """Clear the strip and forget any active LED note state."""

        self.active_notes.clear()
        self.led_driver.clear()
        self.refresh_state()

    def set_playback_hand_mode(self, hand_mode: str) -> dict:
        """Set the current requested playback hand mode."""

        if hand_mode not in {"both", "left", "right"}:
            raise ValueError(f"Unsupported hand mode: {hand_mode}")
        self.playback_hand_mode = hand_mode
        self.refresh_state()
        return self.get_playback_state()

    def get_song_hand_config_state(self, relative_path: str) -> dict:
        """Return saved hand config plus available tracks and channels for one song."""

        if not relative_path:
            raise RuntimeError("A song must be selected before loading hand setup.")
        if self.song_hand_config_store is None:
            raise RuntimeError("Song hand configuration storage is not configured.")
        midi_path = self.song_library.midi_root / relative_path if self.song_library is not None else None
        if midi_path is None:
            raise RuntimeError("Song library is not configured.")
        snapshot = self._reload_song_snapshot()
        selected_song = next((song for song in snapshot["songs"] if song["relative_path"] == relative_path), None)
        if selected_song is None:
            raise RuntimeError(f"Unknown song selection: {relative_path}")
        summary = self.playback.midi_loader.summarize(midi_path, relative_path, selected_song["display_title"])
        config = self.song_hand_config_store.load(relative_path)
        return {
            "config": config.to_dict(),
            "summary": {
                "relative_path": summary.relative_path,
                "display_title": summary.display_title,
                "track_indices": summary.track_indices,
                "channels": summary.channels,
            },
            "invalid": {
                "left_hand_tracks": [value for value in config.left_hand_tracks if value not in summary.track_indices],
                "right_hand_tracks": [value for value in config.right_hand_tracks if value not in summary.track_indices],
                "left_hand_channels": [value for value in config.left_hand_channels if value not in summary.channels],
                "right_hand_channels": [value for value in config.right_hand_channels if value not in summary.channels],
            },
        }

    def save_song_hand_config(
        self,
        relative_path: str,
        left_hand_tracks: list[int],
        right_hand_tracks: list[int],
        left_hand_channels: list[int],
        right_hand_channels: list[int],
    ) -> dict:
        """Persist one song's left/right hand assignment and return the new state."""

        if self.song_hand_config_store is None:
            raise RuntimeError("Song hand configuration storage is not configured.")
        config = SongHandConfig(
            relative_path=relative_path,
            left_hand_tracks=left_hand_tracks,
            right_hand_tracks=right_hand_tracks,
            left_hand_channels=left_hand_channels,
            right_hand_channels=right_hand_channels,
        )
        self.song_hand_config_store.save(config)
        self.refresh_state()
        return self.get_song_hand_config_state(relative_path)

    def start_playback(self) -> dict:
        """Start playback for the currently selected MIDI song."""

        selected_song = self.get_selected_song()
        if selected_song is None:
            raise RuntimeError("No song selected. Choose a MIDI file on the Songs page first.")
        if self.song_library is None or self.song_hand_config_store is None:
            raise RuntimeError("Song playback dependencies are not configured.")

        hand_config = self.song_hand_config_store.load(selected_song["relative_path"])
        if self.playback_hand_mode == "left" and not (hand_config.left_hand_tracks or hand_config.left_hand_channels):
            raise RuntimeError("No left-hand mapping saved for this song yet.")
        if self.playback_hand_mode == "right" and not (hand_config.right_hand_tracks or hand_config.right_hand_channels):
            raise RuntimeError("No right-hand mapping saved for this song yet.")
        hand_state = self.get_song_hand_config_state(selected_song["relative_path"])
        invalid = hand_state["invalid"]
        if self.playback_hand_mode == "left" and (
            hand_config.left_hand_tracks == invalid["left_hand_tracks"]
            and hand_config.left_hand_channels == invalid["left_hand_channels"]
        ):
            raise RuntimeError("Saved left-hand mapping does not match this MIDI file anymore.")
        if self.playback_hand_mode == "right" and (
            hand_config.right_hand_tracks == invalid["right_hand_tracks"]
            and hand_config.right_hand_channels == invalid["right_hand_channels"]
        ):
            raise RuntimeError("Saved right-hand mapping does not match this MIDI file anymore.")

        midi_path = self.song_library.midi_root / selected_song["relative_path"]
        payload = self.playback.play_song(
            midi_path=midi_path,
            relative_path=selected_song["relative_path"],
            display_title=selected_song["display_title"],
            emit_note_event=self.handle_note_event,
            clear_leds=self.clear_leds,
            hand_mode=self.playback_hand_mode,
            hand_config=hand_config,
        )
        self.refresh_state()
        return payload

    def stop_playback(self) -> dict:
        """Stop active playback and return the resulting playback state."""

        payload = self.playback.stop()
        self.refresh_state()
        return payload

    def get_playback_state(self) -> dict:
        """Return the current playback state for the API and UI."""

        self.refresh_state()
        return self.playback.get_state()

    def attach_midi_input(self, midi_input: MidiInputPort) -> None:
        self.midi_input = midi_input
        midi_input.subscribe(self.handle_note_event)
        self.refresh_state()

    def handle_chase_step(self) -> None:
        frame = chase_step(self.settings.led.total_leds, self.chase_index, hex_to_rgb(self.settings.led.note_color))
        for index, color in enumerate(frame):
            self.led_driver.set_pixel(index, color)
        self.led_driver.show()
        self.chase_index = (self.chase_index + 1) % self.settings.led.total_leds
        self.refresh_state()

    def generate_keymap(self, total_leds: int | None = None, first_led: int | None = None, direction: str | None = None) -> dict:
        self.settings.led.total_leds = total_leds or self.settings.led.total_leds
        self.settings.led.default_first_led = first_led if first_led is not None else self.settings.led.default_first_led
        self.settings.led.strip_direction = direction or self.settings.led.strip_direction
        self.keymap = KeymapGenerator().generate(
            total_leds=self.settings.led.total_leds,
            first_led=self.settings.led.default_first_led,
            direction=self.settings.led.strip_direction,
        )
        self.key_mapper = KeyMapper(self.keymap)
        if self.keymap_store is not None:
            self.keymap_store.save(self.keymap)
        if self.settings_store is not None:
            self.settings_store.save(self.settings)
        self.refresh_state()
        return self.keymap.to_dict()

    def start_calibration(self) -> dict:
        note_order = list(range(LOWEST_PIANO_NOTE, HIGHEST_PIANO_NOTE + 1))
        self.calibration_session = CalibrationSession(keymap=self.keymap, note_order=note_order)
        self.full_map_preview_active = False
        self.awaiting_calibration_note = True
        if self.show_full_keyboard_preview_during_calibration:
            self._render_full_keymap_to_strip()
        self.refresh_state()
        return self.calibration_session.to_dict()

    def arm_calibration_note_capture(self) -> dict:
        """Wait for the next live piano key press to select or confirm calibration."""

        if self.calibration_session is None:
            self.start_calibration()
        self.awaiting_calibration_note = True
        self.refresh_state()
        return self.get_calibration_state()

    def stop_calibration(self) -> dict:
        """Exit calibration mode and clear any highlighted selection."""

        self.calibration_session = None
        self.awaiting_calibration_note = False
        self.clear_leds()
        self.refresh_state()
        return self.get_calibration_state()

    def capture_calibration_note(self, note: int) -> dict:
        """Consume the next armed piano key press for calibration workflow."""

        if self.calibration_session is None:
            self.start_calibration()

        assert self.calibration_session is not None
        if self.calibration_session.selected_note is None:
            return self.calibration_select_key(note)
        if self.calibration_session.selected_note == note:
            return self.calibration_confirm(note)
        if note < self.calibration_session.selected_note:
            return self.calibration_shift_piano("left")
        return self.calibration_shift_piano("right")

    def set_calibration_full_preview(self, enabled: bool) -> dict:
        """Toggle whether calibration shows the whole keyboard between edits."""

        self.show_full_keyboard_preview_during_calibration = enabled
        if self.calibration_session is not None and self.calibration_session.selected_note is None:
            if enabled:
                self._render_full_keymap_to_strip()
            else:
                self.clear_leds()
        self.refresh_state()
        return self.get_calibration_state()

    def get_keymap_state(self) -> dict:
        """Return the current keymap plus a few useful summary values."""

        return {
            "note_to_led": self.keymap.to_dict()["note_to_led"],
            "note_count": len(self.keymap.note_to_led),
            "first_note": min(self.keymap.note_to_led) if self.keymap.note_to_led else None,
            "last_note": max(self.keymap.note_to_led) if self.keymap.note_to_led else None,
            "full_map_preview_active": self.full_map_preview_active,
        }

    def get_calibration_state(self) -> dict:
        """Return whether calibration is active and the current session payload."""

        session = self.calibration_session.to_dict() if self.calibration_session else None
        return {
            "active": self.calibration_session is not None,
            "awaiting_note": self.awaiting_calibration_note,
            "show_full_keyboard_preview": self.show_full_keyboard_preview_during_calibration,
            "session": session,
        }

    def calibration_select_key(self, note: int) -> dict:
        if self.calibration_session is None:
            self.start_calibration()
        assert self.calibration_session is not None
        self.full_map_preview_active = False
        self.awaiting_calibration_note = True
        led_index = self.calibration_session.select_key(note)
        self.clear_leds()
        if self._in_led_range(led_index):
            self.led_driver.set_pixel(led_index, self.note_color_for(note))
            self.led_driver.show()
        self.refresh_state()
        return self.calibration_session.to_dict()

    def calibration_shift_piano(self, direction: str) -> dict:
        """Shift the selected LED by physical piano direction instead of raw index."""

        if direction not in {"left", "right"}:
            raise ValueError(f"Unsupported piano direction: {direction}")

        if self.settings.led.strip_direction == "right_to_left":
            delta = 1 if direction == "left" else -1
        else:
            delta = -1 if direction == "left" else 1
        return self.calibration_shift(delta)

    def calibration_shift(self, delta: int) -> dict:
        if self.calibration_session is None:
            raise RuntimeError("Calibration has not started")
        self.awaiting_calibration_note = True
        led_index = self.calibration_session.shift(delta)
        selected = self.calibration_session.selected_note
        self.clear_leds()
        assert selected is not None
        if self._in_led_range(led_index):
            self.led_driver.set_pixel(led_index, self.note_color_for(selected))
            self.led_driver.show()
        self.refresh_state()
        return self.calibration_session.to_dict()

    def calibration_confirm(self, note: int) -> dict:
        if self.calibration_session is None:
            raise RuntimeError("Calibration has not started")
        self.awaiting_calibration_note = True
        self.calibration_session.confirm_key(note)
        if self.show_full_keyboard_preview_during_calibration:
            self._render_full_keymap_to_strip()
        else:
            self.clear_leds()
        if self.keymap_store is not None:
            self.keymap_store.save(self.keymap)
        self.refresh_state()
        return self.calibration_session.to_dict()

    def refresh_state(self) -> None:
        """Publish the latest runtime snapshot for the web layer."""

        calibration = self.calibration_session.to_dict() if self.calibration_session else None
        self.state_store.update(
            settings=self.settings.to_dict(),
            active_notes=sorted(self.active_notes),
            last_note_event=self.last_note_event,
            calibration=calibration,
            keymap=self.keymap.to_dict(),
            songs=self.song_snapshot["songs"],
            selected_song_path=self.song_snapshot["selected_song_path"],
            selected_song=self.song_snapshot["selected_song"],
            playback=self.playback.get_state(),
        )

    def get_state(self) -> dict:
        self.refresh_state()
        return self.state_store.snapshot()
