"""Runtime tests covering live note lighting and calibration capture behavior."""

import unittest

from piano_led.config.settings import AppSettings, LedSettings
from piano_led.core.models import NoteEvent
from piano_led.keymap.models import Keymap
from piano_led.leds.driver_fake import FakeLedDriver
from piano_led.midi.input import FakeMidiInputPort
from piano_led.services.runtime import PianoLedRuntime


class PianoLedRuntimeTest(unittest.TestCase):
    def test_runtime_lights_and_clears_notes_with_black_key_color(self) -> None:
        settings = AppSettings(
            led=LedSettings(
                total_leds=8,
                note_color="#112233",
                black_key_color="#445566",
                use_black_key_color=True,
            )
        )
        driver = FakeLedDriver(total_leds=8)
        runtime = PianoLedRuntime(settings=settings, keymap=Keymap(note_to_led={60: 1, 61: 2}), led_driver=driver)

        runtime.handle_note_event(NoteEvent.note_on(note=60, velocity=90, source="test"))
        runtime.handle_note_event(NoteEvent.note_on(note=61, velocity=90, source="test"))

        self.assertEqual(driver.pixels[1], (17, 34, 51))
        self.assertEqual(driver.pixels[2], (68, 85, 102))

        runtime.handle_note_event(NoteEvent.note_off(note=60, source="test"))
        runtime.handle_note_event(NoteEvent.note_off(note=61, source="test"))

        self.assertEqual(driver.pixels[1], (0, 0, 0))
        self.assertEqual(driver.pixels[2], (0, 0, 0))

    def test_runtime_clear_leds_turns_entire_strip_off(self) -> None:
        settings = AppSettings(led=LedSettings(total_leds=4))
        driver = FakeLedDriver(total_leds=4)
        runtime = PianoLedRuntime(settings=settings, keymap=Keymap(note_to_led={60: 1}), led_driver=driver)

        runtime.handle_note_event(NoteEvent.note_on(note=60, velocity=64, source="test"))
        runtime.clear_leds()

        self.assertEqual(driver.pixels, [(0, 0, 0)] * 4)

    def test_runtime_can_subscribe_to_midi_input(self) -> None:
        settings = AppSettings(led=LedSettings(total_leds=4))
        driver = FakeLedDriver(total_leds=4)
        runtime = PianoLedRuntime(settings=settings, keymap=Keymap(note_to_led={60: 1}), led_driver=driver)
        midi_input = FakeMidiInputPort()

        runtime.attach_midi_input(midi_input)
        midi_input.emit(NoteEvent.note_on(note=60, velocity=99, source="midi"))

        self.assertEqual(driver.pixels[1], (0, 184, 148))

    def test_runtime_can_arm_calibration_and_capture_next_live_key(self) -> None:
        settings = AppSettings(led=LedSettings(total_leds=8))
        driver = FakeLedDriver(total_leds=8)
        runtime = PianoLedRuntime(settings=settings, keymap=Keymap(note_to_led={60: 1, 61: 2}), led_driver=driver)

        runtime.start_calibration()
        armed_state = runtime.arm_calibration_note_capture()

        self.assertTrue(armed_state["awaiting_note"])

        runtime.handle_note_event(NoteEvent.note_on(note=61, velocity=90, source="midi"))
        selected_state = runtime.get_calibration_state()

        self.assertFalse(selected_state["awaiting_note"])
        self.assertEqual(selected_state["session"]["selected_note"], 61)
        self.assertEqual(selected_state["session"]["active_led"], 2)

        runtime.arm_calibration_note_capture()
        runtime.handle_note_event(NoteEvent.note_on(note=61, velocity=90, source="midi"))
        confirmed_state = runtime.get_calibration_state()

        self.assertIsNone(confirmed_state["session"]["selected_note"])
        self.assertIn(61, confirmed_state["session"]["completed_notes"])
