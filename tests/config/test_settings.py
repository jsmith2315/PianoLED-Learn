"""Settings store tests for repo defaults and local-machine overrides."""

import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from piano_led.config.settings import AppSettings, SettingsStore


class SettingsStoreTest(unittest.TestCase):
    def test_settings_store_round_trips_json(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            store = SettingsStore(path)
            settings = AppSettings()
            settings.led.total_leds = 123

            store.save(settings)
            loaded = store.load()

            self.assertEqual(loaded.led.total_leds, 123)

    def test_settings_store_merges_local_override_file(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_path = root / "settings.json"
            local_path = root / "settings.local.json"
            base_path.write_text(
                json.dumps(
                    {
                        "led": {"backend": "fake", "strip_direction": "left_to_right", "total_leds": 176},
                        "midi": {"backend": "fake", "input_port_name": "", "output_port_name": ""},
                        "selected_keymap": "default_88.json",
                    }
                ),
                encoding="utf-8",
            )
            local_path.write_text(
                json.dumps(
                    {
                        "led": {"backend": "rpi_ws281x", "strip_direction": "right_to_left", "default_first_led": 175},
                        "midi": {"backend": "mido", "input_port_name": "Piano Port"},
                    }
                ),
                encoding="utf-8",
            )

            store = SettingsStore(base_path, local_path=local_path)
            loaded = store.load()

            self.assertEqual(loaded.led.backend, "rpi_ws281x")
            self.assertEqual(loaded.led.strip_direction, "right_to_left")
            self.assertEqual(loaded.led.default_first_led, 175)
            self.assertEqual(loaded.midi.backend, "mido")
            self.assertEqual(loaded.midi.input_port_name, "Piano Port")
            self.assertEqual(loaded.selected_keymap, "default_88.json")

    def test_settings_store_saves_machine_specific_updates_to_local_file(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_path = root / "settings.json"
            local_path = root / "settings.local.json"
            base_path.write_text(
                json.dumps(
                    {
                        "led": {"backend": "fake", "strip_direction": "left_to_right"},
                        "midi": {"backend": "fake", "input_port_name": "", "output_port_name": ""},
                        "selected_keymap": "default_88.json",
                    }
                ),
                encoding="utf-8",
            )

            store = SettingsStore(base_path, local_path=local_path)
            settings = store.load()
            settings.led.backend = "rpi_ws281x"
            settings.midi.backend = "mido"
            settings.midi.input_port_name = "Piano Port"
            store.save(settings)

            base_payload = json.loads(base_path.read_text(encoding="utf-8"))
            local_payload = json.loads(local_path.read_text(encoding="utf-8"))

            self.assertEqual(base_payload["led"]["backend"], "fake")
            self.assertEqual(local_payload["led"]["backend"], "rpi_ws281x")
            self.assertEqual(local_payload["midi"]["backend"], "mido")
            self.assertEqual(local_payload["midi"]["input_port_name"], "Piano Port")
