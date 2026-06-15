import unittest

from piano_led.main import main


class SmokeCommandTests(unittest.TestCase):
    def test_led_chase_command_runs(self) -> None:
        self.assertEqual(main(["led-chase", "--steps", "2"]), 0)

    def test_midi_list_command_runs_without_backend(self) -> None:
        self.assertEqual(main(["midi-list-ports"]), 0)
