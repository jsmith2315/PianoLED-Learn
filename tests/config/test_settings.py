import unittest
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
