"""Long-lived runtime behavior for note lighting, calibration, and state."""

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
from piano_led.services.state_store import StateStore


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
    ) -> None:
        self.settings = settings
        self.keymap = keymap
        self.led_driver = led_driver
        self.settings_store = settings_store
        self.keymap_store = keymap_store
        self.state_store = state_store or StateStore()
        self.key_mapper = KeyMapper(keymap)
        self.active_notes: set[int] = set()
        self.last_note_event: dict | None = None
        self.calibration_session: CalibrationSession | None = None
        self.show_full_keyboard_preview_during_calibration = False
        self.full_map_preview_active = False
        self.awaiting_calibration_note = False
        self.chase_index = 0
        self.midi_input: MidiInputPort | None = None
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

    def handle_note_event(self, event: NoteEvent) -> None:
        self.last_note_event = {
            "event_type": event.event_type,
            "note": event.note,
            "velocity": event.velocity,
            "source": event.source,
        }
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
            color = self.note_color_for(event.note)
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

    def note_color_for(self, note: int) -> tuple[int, int, int]:
        if self.settings.led.use_black_key_color and is_black_key(note):
            return hex_to_rgb(self.settings.led.black_key_color)
        return hex_to_rgb(self.settings.led.note_color)

    def clear_leds(self) -> None:
        self.active_notes.clear()
        self.led_driver.clear()
        self.refresh_state()

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
        calibration = self.calibration_session.to_dict() if self.calibration_session else None
        self.state_store.update(
            settings=self.settings.to_dict(),
            active_notes=sorted(self.active_notes),
            last_note_event=self.last_note_event,
            calibration=calibration,
            keymap=self.keymap.to_dict(),
        )

    def get_state(self) -> dict:
        self.refresh_state()
        return self.state_store.snapshot()
