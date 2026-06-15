import unittest

from piano_led.keymap.generator import KeymapGenerator


class KeymapGeneratorTest(unittest.TestCase):
    def test_generator_maps_low_to_high_notes_left_to_right(self) -> None:
        mapping = KeymapGenerator().generate(total_leds=176, first_led=0, direction="left_to_right")
        self.assertEqual(mapping.note_to_led[21], 0)
        self.assertEqual(mapping.note_to_led[108], 175)
        self.assertLess(mapping.note_to_led[40], mapping.note_to_led[41])

    def test_generator_maps_low_to_high_notes_right_to_left(self) -> None:
        mapping = KeymapGenerator().generate(total_leds=176, first_led=175, direction="right_to_left")
        self.assertEqual(mapping.note_to_led[21], 175)
        self.assertEqual(mapping.note_to_led[108], 0)
        self.assertGreater(mapping.note_to_led[40], mapping.note_to_led[41])
