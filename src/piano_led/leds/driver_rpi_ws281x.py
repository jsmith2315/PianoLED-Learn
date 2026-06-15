"""Raspberry Pi WS281X driver integration."""

from __future__ import annotations

import importlib

from piano_led.config.settings import AppSettings
from piano_led.leds.driver_base import LedDriver


class RpiWs281xLedDriver(LedDriver):
    """Adapter around an initialized ``rpi_ws281x.PixelStrip``."""
    def __init__(self, strip) -> None:
        self.strip = strip

    def set_pixel(self, index: int, color: tuple[int, int, int]) -> None:
        self.strip.setPixelColorRGB(index, *color)

    def show(self) -> None:
        self.strip.show()

    def clear(self) -> None:
        for index in range(self.strip.numPixels()):
            self.strip.setPixelColorRGB(index, 0, 0, 0)
        self.strip.show()


def create_rpi_led_driver(settings: AppSettings, ws281x_module=None) -> RpiWs281xLedDriver:
    """Construct and initialize the Pi LED driver from app settings."""
    module = ws281x_module or importlib.import_module("rpi_ws281x")
    strip = module.PixelStrip(
        settings.led.total_leds,
        settings.led.gpio_pin,
        settings.led.pwm_frequency_hz,
        settings.led.dma_channel,
        settings.led.invert_signal,
        settings.led.brightness,
        settings.led.channel,
    )
    strip.begin()
    return RpiWs281xLedDriver(strip)
