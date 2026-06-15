import types
import unittest

from piano_led.config.settings import AppSettings
from piano_led.leds.driver_rpi_ws281x import RpiWs281xLedDriver, create_rpi_led_driver


class FakePixelStrip:
    def __init__(self, *args):
        self.args = args
        self.calls = []
        self.started = False

    def begin(self):
        self.started = True

    def setPixelColorRGB(self, index, red, green, blue):
        self.calls.append(("set", index, red, green, blue))

    def show(self):
        self.calls.append(("show",))

    def numPixels(self):
        return 3


class RpiLedDriverTests(unittest.TestCase):
    def test_create_rpi_led_driver_builds_strip_from_settings(self) -> None:
        fake_module = types.SimpleNamespace(PixelStrip=FakePixelStrip)
        settings = AppSettings()
        settings.led.total_leds = 16
        settings.led.gpio_pin = 18
        settings.led.brightness = 128
        settings.led.dma_channel = 10

        driver = create_rpi_led_driver(settings, ws281x_module=fake_module)

        self.assertIsInstance(driver, RpiWs281xLedDriver)
        self.assertTrue(driver.strip.started)
        self.assertEqual(driver.strip.args[0], 16)
        self.assertEqual(driver.strip.args[1], 18)
