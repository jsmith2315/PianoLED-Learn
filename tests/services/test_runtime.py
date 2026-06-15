"""Runtime tests covering live note lighting and calibration capture behavior."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from piano_led.config.settings import AppSettings, LedSettings
from piano_led.core.models import NoteEvent
from piano_led.keymap.models import Keymap
from piano_led.leds.driver_fake import FakeLedDriver
from piano_led.midi.input import FakeMidiInputPort
from piano_led.services.runtime import PianoLedRuntime
from piano_led.songs.library import SongLibrary


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

        self.assertTrue(selected_state["awaiting_note"])
        self.assertEqual(selected_state["session"]["selected_note"], 61)
        self.assertEqual(selected_state["session"]["active_led"], 2)

        runtime.arm_calibration_note_capture()
        runtime.handle_note_event(NoteEvent.note_on(note=61, velocity=90, source="midi"))
        confirmed_state = runtime.get_calibration_state()

        self.assertIsNone(confirmed_state["session"]["selected_note"])
        self.assertIn(61, confirmed_state["session"]["completed_notes"])

    def test_runtime_calibration_listens_to_live_keys_immediately_after_start(self) -> None:
        settings = AppSettings(led=LedSettings(total_leds=8))
        driver = FakeLedDriver(total_leds=8)
        runtime = PianoLedRuntime(settings=settings, keymap=Keymap(note_to_led={60: 1, 61: 2}), led_driver=driver)

        runtime.start_calibration()
        runtime.handle_note_event(NoteEvent.note_on(note=60, velocity=90, source="midi"))

        selected_state = runtime.get_calibration_state()
        self.assertTrue(selected_state["awaiting_note"])
        self.assertEqual(selected_state["session"]["selected_note"], 60)

        runtime.handle_note_event(NoteEvent.note_off(note=60, source="midi"))
        self.assertEqual(driver.pixels[1], runtime.note_color_for(60))

        runtime.handle_note_event(NoteEvent.note_on(note=60, velocity=90, source="midi"))
        confirmed_state = runtime.get_calibration_state()

        self.assertTrue(confirmed_state["awaiting_note"])
        self.assertIsNone(confirmed_state["session"]["selected_note"])
        self.assertIn(60, confirmed_state["session"]["completed_notes"])

    def test_runtime_shift_left_and_right_follow_piano_direction(self) -> None:
        settings = AppSettings(led=LedSettings(total_leds=16, strip_direction="right_to_left"))
        driver = FakeLedDriver(total_leds=16)
        runtime = PianoLedRuntime(settings=settings, keymap=Keymap(note_to_led={60: 5}), led_driver=driver)

        runtime.start_calibration()
        runtime.calibration_select_key(60)
        runtime.calibration_shift_piano("left")
        self.assertEqual(runtime.keymap.note_to_led[60], 6)

        runtime.calibration_shift_piano("right")
        self.assertEqual(runtime.keymap.note_to_led[60], 5)

    def test_runtime_can_stop_calibration_and_clear_selection(self) -> None:
        settings = AppSettings(led=LedSettings(total_leds=8))
        driver = FakeLedDriver(total_leds=8)
        runtime = PianoLedRuntime(settings=settings, keymap=Keymap(note_to_led={60: 1}), led_driver=driver)

        runtime.start_calibration()
        runtime.handle_note_event(NoteEvent.note_on(note=60, velocity=90, source="midi"))
        stopped_state = runtime.stop_calibration()

        self.assertFalse(stopped_state["active"])
        self.assertFalse(stopped_state["awaiting_note"])
        self.assertIsNone(stopped_state["session"])
        self.assertEqual(driver.pixels[1], (0, 0, 0))

    def test_runtime_state_keeps_last_note_event_for_ui(self) -> None:
        settings = AppSettings(led=LedSettings(total_leds=8))
        driver = FakeLedDriver(total_leds=8)
        runtime = PianoLedRuntime(settings=settings, keymap=Keymap(note_to_led={60: 1}), led_driver=driver)

        runtime.handle_note_event(NoteEvent.note_on(note=60, velocity=70, source="midi"))
        state = runtime.get_state()

        self.assertEqual(
            state["last_note_event"],
            {"event_type": "note_on", "note": 60, "velocity": 70, "source": "midi"},
        )

    def test_runtime_can_preview_full_keymap_with_black_and_white_colors(self) -> None:
        settings = AppSettings(
            led=LedSettings(total_leds=8, note_color="#112233", black_key_color="#445566", use_black_key_color=True)
        )
        driver = FakeLedDriver(total_leds=8)
        runtime = PianoLedRuntime(settings=settings, keymap=Keymap(note_to_led={60: 1, 61: 2}), led_driver=driver)

        preview_state = runtime.preview_full_keymap()

        self.assertTrue(preview_state["full_map_preview_active"])
        self.assertEqual(driver.pixels[1], (17, 34, 51))
        self.assertEqual(driver.pixels[2], (68, 85, 102))

    def test_runtime_can_shift_whole_keymap_by_piano_direction(self) -> None:
        settings = AppSettings(led=LedSettings(total_leds=16, strip_direction="right_to_left"))
        driver = FakeLedDriver(total_leds=16)
        runtime = PianoLedRuntime(settings=settings, keymap=Keymap(note_to_led={60: 5, 61: 7}), led_driver=driver)

        keymap_state = runtime.shift_full_keymap_piano("left")

        self.assertEqual(keymap_state["note_to_led"]["60"], 6)
        self.assertEqual(keymap_state["note_to_led"]["61"], 8)

    def test_runtime_uses_neighboring_piano_keys_to_nudge_selected_mapping(self) -> None:
        settings = AppSettings(led=LedSettings(total_leds=16, strip_direction="right_to_left"))
        driver = FakeLedDriver(total_leds=16)
        runtime = PianoLedRuntime(settings=settings, keymap=Keymap(note_to_led={59: 4, 60: 5, 61: 6}), led_driver=driver)

        runtime.start_calibration()
        runtime.handle_note_event(NoteEvent.note_on(note=60, velocity=90, source="midi"))
        runtime.handle_note_event(NoteEvent.note_on(note=59, velocity=90, source="midi"))
        self.assertEqual(runtime.keymap.note_to_led[60], 6)

        runtime.handle_note_event(NoteEvent.note_on(note=61, velocity=90, source="midi"))
        self.assertEqual(runtime.keymap.note_to_led[60], 5)

    def test_runtime_restores_full_preview_after_confirming_calibration_key(self) -> None:
        settings = AppSettings(
            led=LedSettings(total_leds=8, note_color="#112233", black_key_color="#445566", use_black_key_color=True)
        )
        driver = FakeLedDriver(total_leds=8)
        runtime = PianoLedRuntime(settings=settings, keymap=Keymap(note_to_led={60: 1, 61: 2}), led_driver=driver)

        runtime.set_calibration_full_preview(True)
        runtime.start_calibration()
        self.assertEqual(driver.pixels[1], (17, 34, 51))
        self.assertEqual(driver.pixels[2], (68, 85, 102))

        runtime.handle_note_event(NoteEvent.note_on(note=60, velocity=90, source="midi"))
        self.assertEqual(driver.pixels[1], (17, 34, 51))
        self.assertEqual(driver.pixels[2], (0, 0, 0))

        runtime.handle_note_event(NoteEvent.note_on(note=60, velocity=90, source="midi"))
        self.assertEqual(driver.pixels[1], (17, 34, 51))
        self.assertEqual(driver.pixels[2], (68, 85, 102))

    def test_runtime_can_select_a_valid_song_from_library(self) -> None:
        settings = AppSettings(led=LedSettings(total_leds=8))
        driver = FakeLedDriver(total_leds=8)
        with TemporaryDirectory() as tmp:
            midi_root = Path(tmp)
            midi_root.joinpath("etude.mid").write_bytes(b"mid")
            runtime = PianoLedRuntime(
                settings=settings,
                keymap=Keymap(note_to_led={60: 1}),
                led_driver=driver,
                song_library=SongLibrary(midi_root),
            )

            selection = runtime.select_song("etude.mid")

            self.assertEqual(selection["selected_song_path"], "etude.mid")
            self.assertEqual(selection["selected_song"]["display_title"], "etude")

    def test_runtime_rejects_unknown_song_selection(self) -> None:
        settings = AppSettings(led=LedSettings(total_leds=8))
        driver = FakeLedDriver(total_leds=8)
        with TemporaryDirectory() as tmp:
            runtime = PianoLedRuntime(
                settings=settings,
                keymap=Keymap(note_to_led={60: 1}),
                led_driver=driver,
                song_library=SongLibrary(Path(tmp)),
            )

            with self.assertRaises(ValueError):
                runtime.select_song("missing.mid")
