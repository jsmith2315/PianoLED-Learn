import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from piano_led.app import build_application
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
