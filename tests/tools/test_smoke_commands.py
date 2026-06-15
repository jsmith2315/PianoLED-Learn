import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
import json

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

    def test_keymap_generate_command_updates_saved_settings_and_map(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings_dir = root / "data" / "settings"
            keymaps_dir = root / "data" / "keymaps"
            settings_dir.mkdir(parents=True, exist_ok=True)
            keymaps_dir.mkdir(parents=True, exist_ok=True)
            settings_dir.joinpath("settings.json").write_text(
                json.dumps(
                    {
                        "led": {
                            "total_leds": 176,
                            "leds_per_meter": 144,
                            "note_color": "#00b894",
                            "black_key_color": "#0984e3",
                            "use_black_key_color": True,
                            "strip_direction": "left_to_right",
                            "default_first_led": 0,
                            "backend": "fake",
                            "gpio_pin": 18,
                            "brightness": 128,
                            "dma_channel": 10,
                            "pwm_frequency_hz": 800000,
                            "invert_signal": False,
                            "channel": 0,
                        },
                        "midi": {"backend": "fake", "input_port_name": "", "output_port_name": ""},
                        "selected_keymap": "default_88.json",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            keymaps_dir.joinpath("default_88.json").write_text('{"note_to_led": {}}', encoding="utf-8")

            self.assertEqual(
                main(
                    [
                        "--project-root",
                        str(root),
                        "keymap-generate",
                        "--direction",
                        "right_to_left",
                        "--first-led",
                        "175",
                        "--total-leds",
                        "176",
                    ]
                ),
                0,
            )

            settings = json.loads(settings_dir.joinpath("settings.json").read_text(encoding="utf-8"))
            keymap = json.loads(keymaps_dir.joinpath("default_88.json").read_text(encoding="utf-8"))
            self.assertEqual(settings["led"]["strip_direction"], "right_to_left")
            self.assertEqual(settings["led"]["default_first_led"], 175)
            self.assertEqual(keymap["note_to_led"]["21"], 175)

    def test_web_serve_command_can_run_for_bounded_duration(self) -> None:
        class FakeServer:
            def __init__(self):
                self.timeout = None
                self.calls = 0

            def handle_request(self):
                self.calls += 1

            def server_close(self):
                self.calls += 100

        fake_runtime = type("Runtime", (), {"describe": lambda self: "runtime ok"})()
        fake_application = type("App", (), {"runtime": fake_runtime})()
        fake_server = FakeServer()

        with patch("piano_led.main.build_application", return_value=fake_application), patch(
            "piano_led.main.make_server", return_value=fake_server
        ):
            self.assertEqual(main(["web-serve", "--host", "0.0.0.0", "--port", "8080", "--seconds", "0"]), 0)

        self.assertGreaterEqual(fake_server.calls, 100)
