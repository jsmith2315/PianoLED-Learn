import unittest

from piano_led.main import main


class EntrypointTest(unittest.TestCase):
    def test_main_starts_cleanly(self) -> None:
        self.assertEqual(main(), 0)

