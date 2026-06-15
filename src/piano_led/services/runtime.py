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
        self.calibration_session: CalibrationSession | None = None
        self.chase_index = 0
        self.midi_input: MidiInputPort | None = None
        self.refresh_state()

    def describe(self) -> str:
        return (
            f"Piano LED runtime ready: leds={self.settings.led.total_leds}, "
            f"keymap_notes={len(self.keymap.note_to_led)}, "
            f"calibration_active={self.calibration_session is not None}"
        )

    def handle_note_event(self, event: NoteEvent) -> None:
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
        self.refresh_state()
        return self.calibration_session.to_dict()

    def calibration_select_key(self, note: int) -> dict:
        if self.calibration_session is None:
            self.start_calibration()
        assert self.calibration_session is not None
        led_index = self.calibration_session.select_key(note)
        self.clear_leds()
        self.led_driver.set_pixel(led_index, self.note_color_for(note))
        self.led_driver.show()
        self.refresh_state()
        return self.calibration_session.to_dict()

    def calibration_shift(self, delta: int) -> dict:
        if self.calibration_session is None:
            raise RuntimeError("Calibration has not started")
        led_index = self.calibration_session.shift(delta)
        selected = self.calibration_session.selected_note
        self.clear_leds()
        assert selected is not None
        self.led_driver.set_pixel(led_index, self.note_color_for(selected))
        self.led_driver.show()
        self.refresh_state()
        return self.calibration_session.to_dict()

    def calibration_confirm(self, note: int) -> dict:
        if self.calibration_session is None:
            raise RuntimeError("Calibration has not started")
        self.calibration_session.confirm_key(note)
        if self.keymap_store is not None:
            self.keymap_store.save(self.keymap)
        self.refresh_state()
        return self.calibration_session.to_dict()

    def refresh_state(self) -> None:
        calibration = self.calibration_session.to_dict() if self.calibration_session else None
        self.state_store.update(
            settings=self.settings.to_dict(),
            active_notes=sorted(self.active_notes),
            calibration=calibration,
            keymap=self.keymap.to_dict(),
        )

    def get_state(self) -> dict:
        self.refresh_state()
        return self.state_store.snapshot()
