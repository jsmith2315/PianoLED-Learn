"""Runtime tests covering live note lighting and calibration capture behavior."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from piano_led.config.settings import AppSettings, LedSettings
from piano_led.core.models import NoteEvent
from piano_led.keymap.models import Keymap
from piano_led.leds.driver_fake import FakeLedDriver
from piano_led.midi.input import FakeMidiInputPort
from piano_led.midi.output import FakeMidiOutputPort
from piano_led.services.runtime import PianoLedRuntime
from piano_led.songs.library import SongLibrary


class PianoLedRuntimeTest(unittest.TestCase):
    def test_runtime_refresh_state_uses_cached_song_snapshot_without_rescanning(self) -> None:
        class CountingSongLibrary:
            def __init__(self) -> None:
                self.calls = 0

            def list_songs(self) -> list[dict]:
                self.calls += 1
                return [
                    {
                        "file_name": "etude.mid",
                        "relative_path": "etude.mid",
                        "display_title": "etude",
                    }
                ]

        settings = AppSettings(led=LedSettings(total_leds=8))
        driver = FakeLedDriver(total_leds=8)
        song_library = CountingSongLibrary()
        runtime = PianoLedRuntime(
            settings=settings,
            keymap=Keymap(note_to_led={60: 1}),
            led_driver=driver,
            song_library=song_library,
        )
        runtime.select_song("etude.mid")
        song_library.calls = 0

        runtime.refresh_state()

        self.assertEqual(song_library.calls, 0)
        self.assertEqual(runtime.get_state()["selected_song"]["relative_path"], "etude.mid")

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

    def test_runtime_can_run_a_multi_step_chase_test_and_clear_afterward(self) -> None:
        settings = AppSettings(led=LedSettings(total_leds=5))
        driver = FakeLedDriver(total_leds=5)
        runtime = PianoLedRuntime(settings=settings, keymap=Keymap(note_to_led={60: 1}), led_driver=driver)

        payload = runtime.run_chase_test(steps=4, delay_ms=0.0, clear_after=True)

        self.assertEqual(payload["steps"], 4)
        self.assertEqual(payload["chase_index"], 4)
        self.assertEqual(driver.pixels, [(0, 0, 0)] * 5)
        self.assertGreaterEqual(driver.show_count, 5)

    def test_runtime_can_subscribe_to_midi_input(self) -> None:
        settings = AppSettings(led=LedSettings(total_leds=4))
        driver = FakeLedDriver(total_leds=4)
        runtime = PianoLedRuntime(settings=settings, keymap=Keymap(note_to_led={60: 1}), led_driver=driver)
        midi_input = FakeMidiInputPort()

        runtime.attach_midi_input(midi_input)
        midi_input.emit(NoteEvent.note_on(note=60, velocity=99, source="midi"))

        self.assertEqual(driver.pixels[1], (0, 184, 148))

    def test_runtime_can_replace_live_midi_input_without_leaving_old_subscription_attached(self) -> None:
        settings = AppSettings(led=LedSettings(total_leds=4))
        driver = FakeLedDriver(total_leds=4)
        runtime = PianoLedRuntime(
            settings=settings,
            keymap=Keymap(note_to_led={60: 1, 62: 2}),
            led_driver=driver,
            midi_output=FakeMidiOutputPort(),
        )
        first_input = FakeMidiInputPort()
        second_input = FakeMidiInputPort()

        runtime.attach_midi_input(first_input)
        runtime.replace_midi_input(second_input)

        first_input.emit(NoteEvent.note_on(note=60, velocity=99, source="old"))
        self.assertEqual(driver.pixels[1], (0, 0, 0))

        second_input.emit(NoteEvent.note_on(note=62, velocity=99, source="new"))
        self.assertEqual(driver.pixels[2], (0, 184, 148))

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

    def test_runtime_clears_stale_song_selection_consistently_when_song_disappears(self) -> None:
        settings = AppSettings(led=LedSettings(total_leds=8))
        driver = FakeLedDriver(total_leds=8)
        with TemporaryDirectory() as tmp:
            midi_root = Path(tmp)
            song_path = midi_root / "etude.mid"
            song_path.write_bytes(b"mid")
            runtime = PianoLedRuntime(
                settings=settings,
                keymap=Keymap(note_to_led={60: 1}),
                led_driver=driver,
                song_library=SongLibrary(midi_root),
            )

            runtime.select_song("etude.mid")
            song_path.unlink()

            selection = runtime.get_song_selection_state()
            state = runtime.get_state()

            self.assertIsNone(selection["selected_song_path"])
            self.assertIsNone(selection["selected_song"])
            self.assertIsNone(runtime.selected_song_path)
            self.assertIsNone(state["selected_song_path"])
            self.assertIsNone(state["selected_song"])
