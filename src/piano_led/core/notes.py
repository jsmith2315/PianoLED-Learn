from __future__ import annotations


BLACK_KEY_CLASSES = {1, 3, 6, 8, 10}
LOWEST_PIANO_NOTE = 21
HIGHEST_PIANO_NOTE = 108


def is_black_key(note: int) -> bool:
    return note % 12 in BLACK_KEY_CLASSES

