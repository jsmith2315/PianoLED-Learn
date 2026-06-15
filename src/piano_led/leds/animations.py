from __future__ import annotations


def chase_step(total_leds: int, current_index: int, color: tuple[int, int, int]) -> list[tuple[int, int, int]]:
    frame = [(0, 0, 0)] * total_leds
    frame[current_index % total_leds] = color
    return frame

