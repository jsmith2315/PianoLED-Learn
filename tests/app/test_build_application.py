import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from piano_led.app import build_application
from piano_led.midi.input import FakeMidiInputPort
from piano_led.midi.output import FakeMidiOutputPort


class BuildApplicationTest(unittest.TestCase):
    def test_build_application_uses_fake_backends_by_default(self) -> None:
        with TemporaryDirectory() as tmp:
            application = build_application(Path(tmp))

        self.assertIsInstance(application.midi_input, FakeMidiInputPort)
        self.assertIsInstance(application.midi_output, FakeMidiOutputPort)

