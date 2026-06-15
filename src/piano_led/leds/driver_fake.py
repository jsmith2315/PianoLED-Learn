"""In-memory LED driver for tests and non-hardware development."""

from __future__ import annotations

from piano_led.leds.driver_base import LedDriver


class FakeLedDriver(LedDriver):
    """Simple pixel buffer that mimics an LED strip in memory."""
    def __init__(self, total_leds: int) -> None:
        self.total_leds = total_leds
        self.pixels = [(0, 0, 0)] * total_leds
        self.show_count = 0

    def set_pixel(self, index: int, color: tuple[int, int, int]) -> None:
        self.pixels[index] = color

    def show(self) -> None:
        self.show_count += 1

    def clear(self) -> None:
        self.pixels = [(0, 0, 0)] * self.total_leds
        self.show()
