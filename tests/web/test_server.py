import io
import json
import unittest

from piano_led.app import build_application
from piano_led.web.server import create_web_app


def _invoke(app, method: str, path: str, body: bytes = b""):
    captured = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }
    payload = b"".join(app(environ, start_response))
    return captured["status"], dict(captured["headers"]), payload


class WebServerTest(unittest.TestCase):
    def test_web_app_exposes_runtime_state_and_clear_action(self) -> None:
        application = build_application()
        app = create_web_app(application.runtime)

        status, headers, payload = _invoke(app, "GET", "/api/state")
        state = json.loads(payload.decode("utf-8"))
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertGreaterEqual(state["settings"]["led"]["total_leds"], 88)

        application.runtime.handle_chase_step()
        status, _, _ = _invoke(app, "POST", "/api/led/clear", b"{}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(application.runtime.led_driver.pixels[0], (0, 0, 0))

    def test_keymap_page_and_api_expose_generation_and_calibration_state(self) -> None:
        application = build_application()
        app = create_web_app(application.runtime)

        status, headers, payload = _invoke(app, "GET", "/keymap")
        html = payload.decode("utf-8")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("Generate Base Keymap", html)
        self.assertIn("Calibration Controls", html)
        self.assertIn("right_to_left", html)

        status, headers, payload = _invoke(app, "GET", "/api/keymap")
        keymap_state = json.loads(payload.decode("utf-8"))
        self.assertEqual(status, "200 OK")
        self.assertIn("note_to_led", keymap_state)

        status, _, payload = _invoke(app, "GET", "/api/calibration/state")
        calibration_state = json.loads(payload.decode("utf-8"))
        self.assertEqual(calibration_state["active"], False)

        status, _, payload = _invoke(app, "POST", "/api/calibration/start", b"{}")
        calibration_state = json.loads(payload.decode("utf-8"))
        self.assertEqual(calibration_state["active"], True)
        self.assertIn("remaining_notes", calibration_state["session"])

    def test_settings_api_can_flip_strip_direction(self) -> None:
        application = build_application()
        app = create_web_app(application.runtime)

        status, _, payload = _invoke(
            app,
            "POST",
            "/api/settings",
            b'{"led": {"strip_direction": "right_to_left", "default_first_led": 175}}',
        )
        settings = json.loads(payload.decode("utf-8"))

        self.assertEqual(status, "200 OK")
        self.assertEqual(settings["led"]["strip_direction"], "right_to_left")
        self.assertEqual(settings["led"]["default_first_led"], 175)
