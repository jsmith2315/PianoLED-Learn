import unittest

from piano_led.keymap.calibrator import CalibrationSession
from piano_led.keymap.models import Keymap


class CalibrationSessionTest(unittest.TestCase):
    def test_calibration_shift_and_confirm_updates_only_selected_note(self) -> None:
        keymap = Keymap(note_to_led={21: 0, 22: 2, 23: 4})
        session = CalibrationSession(keymap=keymap, note_order=[21, 22, 23])

        self.assertEqual(session.select_key(22), 2)
        self.assertEqual(session.shift(1), 3)
        confirmed = session.confirm_key(22)

        self.assertTrue(confirmed)
        self.assertEqual(session.keymap.note_to_led[21], 0)
        self.assertEqual(session.keymap.note_to_led[22], 3)
        self.assertEqual(session.completed_notes, [22])
