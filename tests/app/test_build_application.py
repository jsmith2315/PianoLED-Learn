import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from piano_led.app import apply_midi_ports, build_application
from piano_led.config.settings import AppSettings, LedSettings, MidiSettings
from piano_led.midi.input import FakeMidiInputPort
from piano_led.midi.output import FakeMidiOutputPort
from piano_led.leds.driver_fake import FakeLedDriver


class BuildApplicationTest(unittest.TestCase):
    def test_build_application_uses_fake_backends_by_default(self) -> None:
        with TemporaryDirectory() as tmp:
            application = build_application(Path(tmp))

        self.assertIsInstance(application.midi_input, FakeMidiInputPort)
        self.assertIsInstance(application.midi_output, FakeMidiOutputPort)

    def test_build_application_can_skip_real_led_initialization(self) -> None:
        with TemporaryDirectory() as tmp:
            with patch("piano_led.app.create_rpi_led_driver", side_effect=AssertionError("should not init real leds")):
                settings_path = Path(tmp) / "data" / "settings" / "settings.json"
                settings_path.parent.mkdir(parents=True, exist_ok=True)
                settings_path.write_text(
                    """
{
  "led": {"backend": "rpi_ws281x", "total_leds": 16},
  "midi": {"backend": "fake", "input_port_name": "", "output_port_name": ""},
  "selected_keymap": "default_88.json"
}
""".strip(),
                    encoding="utf-8",
                )
                application = build_application(Path(tmp), initialize_leds=False)

        self.assertIsInstance(application.runtime.led_driver, FakeLedDriver)

    def test_build_application_wires_song_library_from_project_data_directory(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            songs_root = root / "data" / "songs" / "midi"
            songs_root.mkdir(parents=True, exist_ok=True)
            songs_root.joinpath("nocturne.mid").write_bytes(b"mid")

            application = build_application(root)
            self.assertEqual(
                application.runtime.list_songs(),
                [
                    {
                        "file_name": "nocturne.mid",
                        "relative_path": "nocturne.mid",
                        "display_title": "nocturne",
                    }
                ],
            )

    def test_apply_midi_ports_swaps_runtime_ports_and_persists_names(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            application = build_application(root)
            application.runtime.settings = AppSettings(
                led=LedSettings(total_leds=16),
                midi=MidiSettings(backend="mido", input_port_name="Old In", output_port_name="Old Out"),
            )
            new_input = FakeMidiInputPort()
            new_output = FakeMidiOutputPort()

            with patch("piano_led.app.create_midi_input", return_value=new_input), patch(
                "piano_led.app.create_midi_output", return_value=new_output
            ):
                payload = apply_midi_ports(application, input_port_name="New In", output_port_name="New Out")

        self.assertEqual(payload["input_port_name"], "New In")
        self.assertEqual(payload["output_port_name"], "New Out")
        self.assertIs(application.midi_input, new_input)
        self.assertIs(application.midi_output, new_output)
        self.assertEqual(application.runtime.settings.midi.input_port_name, "New In")
        self.assertEqual(application.runtime.settings.midi.output_port_name, "New Out")
