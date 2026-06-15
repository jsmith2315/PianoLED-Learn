import unittest

from piano_led.core.notes import is_black_key


class NotesTest(unittest.TestCase):
    def test_is_black_key_distinguishes_white_and_black_notes(self) -> None:
        self.assertFalse(is_black_key(60))
        self.assertTrue(is_black_key(61))
        self.assertFalse(is_black_key(62))
