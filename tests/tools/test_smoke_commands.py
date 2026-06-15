import unittest
from unittest.mock import patch

from piano_led.main import main
from piano_led.midi.input import MidoMidiInputPort


class SmokeCommandTests(unittest.TestCase):
    def test_led_chase_command_runs(self) -> None:
        self.assertEqual(main(["led-chase", "--steps", "2"]), 0)

    def test_led_chase_command_waits_between_steps(self) -> None:
        with patch("piano_led.main.time.sleep") as sleep_mock:
            self.assertEqual(main(["led-chase", "--steps", "3", "--delay-ms", "25"]), 0)
        self.assertEqual(sleep_mock.call_count, 3)

    def test_midi_list_command_runs_without_backend(self) -> None:
        self.assertEqual(main(["midi-list-ports"]), 0)

    def test_midi_monitor_command_can_run_for_bounded_duration(self) -> None:
        fake_port = MidoMidiInputPort(port_name="Test Port", mido_module=object())
        fake_port.open = lambda: None
        fake_application = type("App", (), {"midi_input": fake_port})()

        with patch("piano_led.main.build_application", return_value=fake_application):
            self.assertEqual(main(["midi-monitor", "--seconds", "0"]), 0)

    def test_run_live_command_can_run_for_bounded_duration(self) -> None:
        fake_port = MidoMidiInputPort(port_name="Test Port", mido_module=object())
        fake_port.open = lambda: None
        fake_runtime = type("Runtime", (), {"describe": lambda self: "runtime ok"})()
        fake_application = type("App", (), {"midi_input": fake_port, "runtime": fake_runtime})()

        with patch("piano_led.main.build_application", return_value=fake_application):
            self.assertEqual(main(["run-live", "--seconds", "0"]), 0)

    def test_status_command_skips_real_led_initialization(self) -> None:
        fake_runtime = type("Runtime", (), {"describe": lambda self: "runtime ok"})()
        fake_application = type("App", (), {"runtime": fake_runtime})()

        with patch("piano_led.main.build_application", return_value=fake_application) as build_mock:
            self.assertEqual(main(["status"]), 0)

        self.assertEqual(build_mock.call_args.kwargs["initialize_leds"], False)
