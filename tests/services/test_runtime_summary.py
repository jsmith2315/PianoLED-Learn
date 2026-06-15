import unittest

from piano_led.config.settings import AppSettings, LedSettings, MidiSettings
from piano_led.keymap.models import Keymap
from piano_led.leds.driver_fake import FakeLedDriver
from piano_led.services.runtime import PianoLedRuntime


class RuntimeSummaryTest(unittest.TestCase):
    def test_runtime_describe_includes_selected_backends(self) -> None:
        settings = AppSettings(
            led=LedSettings(total_leds=8, backend="rpi_ws281x"),
            midi=MidiSettings(backend="mido", input_port_name="Digital Piano", output_port_name=""),
        )
        runtime = PianoLedRuntime(settings=settings, keymap=Keymap(note_to_led={60: 1}), led_driver=FakeLedDriver(8))

        summary = runtime.describe()

        self.assertIn("led_backend=rpi_ws281x", summary)
        self.assertIn("midi_backend=mido", summary)
        self.assertIn("midi_in=Digital Piano", summary)
