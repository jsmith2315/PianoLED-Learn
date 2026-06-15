from __future__ import annotations

import json
from urllib.parse import parse_qs

from piano_led.services.runtime import PianoLedRuntime


INDEX_HTML = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Piano LED Learn</title>
    <style>
      body { font-family: Georgia, serif; margin: 2rem; background: linear-gradient(120deg, #f4efe6, #dfe9f3); color: #1f2a37; }
      nav a { margin-right: 1rem; color: #0f4c81; text-decoration: none; font-weight: bold; }
      .card { background: rgba(255,255,255,0.85); padding: 1rem 1.25rem; border-radius: 16px; max-width: 42rem; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }
      code { background: #edf2f7; padding: 0.1rem 0.3rem; border-radius: 4px; }
    </style>
  </head>
  <body>
    <nav>
      <a href="/">Home</a>
      <a href="/settings">Settings</a>
      <a href="/keymap">Keymap</a>
      <a href="/songs">Songs</a>
      <a href="/practice">Practice</a>
    </nav>
    <div class="card">
      <h1>Piano LED Learn</h1>
      <p>This early foundation build exposes the runtime, settings, keymap generation, LED tools, and calibration APIs.</p>
      <p>Primary API endpoint: <code>/api/state</code></p>
    </div>
  </body>
</html>
"""


def _json_response(start_response, payload: dict, status: str = "200 OK"):
    body = json.dumps(payload).encode("utf-8")
    start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(body)))])
    return [body]


def _html_response(start_response, body: str):
    payload = body.encode("utf-8")
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(payload)))])
    return [payload]


def create_web_app(runtime: PianoLedRuntime):
    def application(environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")
        length = int(environ.get("CONTENT_LENGTH", "0") or "0")
        raw_body = environ["wsgi.input"].read(length) if length else b""
        body = json.loads(raw_body.decode("utf-8")) if raw_body else {}

        if method == "GET" and path in {"/", "/settings", "/keymap", "/songs", "/practice"}:
            return _html_response(start_response, INDEX_HTML)

        if method == "GET" and path == "/api/state":
            return _json_response(start_response, runtime.get_state())

        if method == "GET" and path == "/api/settings":
            return _json_response(start_response, runtime.settings.to_dict())

        if method == "POST" and path == "/api/settings":
            led_payload = body.get("led", {})
            for key, value in led_payload.items():
                if hasattr(runtime.settings.led, key):
                    setattr(runtime.settings.led, key, value)
            if runtime.settings_store is not None:
                runtime.settings_store.save(runtime.settings)
            runtime.refresh_state()
            return _json_response(start_response, runtime.settings.to_dict())

        if method == "POST" and path == "/api/led/clear":
            runtime.clear_leds()
            return _json_response(start_response, {"ok": True})

        if method == "POST" and path == "/api/led/chase":
            runtime.handle_chase_step()
            return _json_response(start_response, {"ok": True, "chase_index": runtime.chase_index})

        if method == "POST" and path == "/api/keymap/generate":
            payload = runtime.generate_keymap(
                total_leds=body.get("total_leds"),
                first_led=body.get("first_led"),
                direction=body.get("direction"),
            )
            return _json_response(start_response, payload)

        if method == "POST" and path == "/api/calibration/start":
            return _json_response(start_response, runtime.start_calibration())

        if method == "POST" and path == "/api/calibration/select":
            return _json_response(start_response, runtime.calibration_select_key(int(body["note"])))

        if method == "POST" and path == "/api/calibration/shift":
            return _json_response(start_response, runtime.calibration_shift(int(body["delta"])))

        if method == "POST" and path == "/api/calibration/confirm":
            return _json_response(start_response, runtime.calibration_confirm(int(body["note"])))

        if method == "GET" and path == "/health":
            return _json_response(start_response, {"status": "ok"})

        return _json_response(start_response, {"error": "not_found", "path": path}, status="404 Not Found")

    return application

