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
