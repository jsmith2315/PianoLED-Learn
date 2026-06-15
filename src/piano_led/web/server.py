"""Minimal WSGI app for the tablet/browser control surface."""

from __future__ import annotations

import json

from piano_led.services.runtime import PianoLedRuntime


BASE_STYLE = """
      body { font-family: Georgia, serif; margin: 2rem; background: linear-gradient(120deg, #f4efe6, #dfe9f3); color: #1f2a37; }
      nav a { margin-right: 1rem; color: #0f4c81; text-decoration: none; font-weight: bold; }
      .card { background: rgba(255,255,255,0.85); padding: 1rem 1.25rem; border-radius: 16px; max-width: 60rem; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }
      .grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }
      .panel { background: #ffffffcc; padding: 1rem; border-radius: 14px; }
      button { background: #0f4c81; color: white; border: 0; border-radius: 999px; padding: 0.6rem 1rem; cursor: pointer; }
      input, select { width: 100%; margin: 0.3rem 0 0.8rem; padding: 0.45rem; border-radius: 8px; border: 1px solid #cdd6df; }
      code, pre { background: #edf2f7; padding: 0.1rem 0.3rem; border-radius: 4px; }
      pre { padding: 0.8rem; overflow: auto; }
"""


INDEX_HTML = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Piano LED Learn</title>
    <style>
""" + BASE_STYLE + """
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


KEYMAP_HTML = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Piano LED Learn - Keymap</title>
    <style>
""" + BASE_STYLE + """
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
      <h1>Keymap Setup</h1>
      <p>Generate a base mapping first, then use calibration controls to correct each key on the real piano.</p>
      <div class="grid">
        <section class="panel">
          <h2>Generate Base Keymap</h2>
          <label>Total LEDs</label>
          <input id="total-leds" type="number" value="176">
          <label>First LED</label>
          <input id="first-led" type="number" value="0">
          <label>Direction</label>
          <select id="direction">
            <option value="left_to_right">Left to Right</option>
            <option value="right_to_left">Right to Left</option>
          </select>
          <button onclick="generateKeymap()">Generate Keymap</button>
        </section>
        <section class="panel">
          <h2>Calibration Controls</h2>
          <label>Selected Note</label>
          <input id="selected-note" type="number" value="60">
          <button onclick="startCalibration()">Start Calibration</button>
          <button onclick="armNextKey()">Use Next Piano Key</button>
          <button onclick="selectKey()">Select Key</button>
          <button onclick="shiftLed(-1)">Shift Left</button>
          <button onclick="shiftLed(1)">Shift Right</button>
          <button onclick="confirmKey()">Confirm Key</button>
        </section>
      </div>
      <section class="panel">
        <h2>Live Runtime</h2>
        <p>When the server is started with <code>--with-live</code>, this box should update as you play.</p>
        <pre id="live-output">Waiting for live state...</pre>
      </section>
      <section class="panel">
        <h2>What to Expect</h2>
        <p>Generate Base Keymap saves a first-pass map using the current LED count, first LED, and direction.</p>
        <p>Start Calibration marks calibration active. Use Next Piano Key arms the page to capture the next real note you play.</p>
        <p>If no note is selected yet, the next piano key chooses that note and lights its current LED. If the same note is already selected, pressing it again saves the mapping.</p>
        <p>Shift Left and Shift Right move the selected note's LED index. Confirm Key saves that note and clears the current selection.</p>
      </section>
      <section class="panel">
        <h2>Current Keymap Summary</h2>
        <pre id="keymap-output">Loading...</pre>
      </section>
      <section class="panel">
        <h2>Calibration State</h2>
        <pre id="calibration-output">Not started.</pre>
      </section>
      <section class="panel">
        <h2>Last Response</h2>
        <pre id="response-output">No action yet.</pre>
      </section>
    </div>
    <script>
      async function fetchJson(url, options) {
        const response = await fetch(url, options);
        return await response.json();
      }

      async function refreshState() {
        const liveState = await fetchJson('/api/state');
        const keymap = await fetchJson('/api/keymap');
        const calibration = await fetchJson('/api/calibration/state');
        const settings = await fetchJson('/api/settings');
        document.getElementById('total-leds').value = settings.led.total_leds;
        document.getElementById('first-led').value = settings.led.default_first_led;
        document.getElementById('direction').value = settings.led.strip_direction;
        document.getElementById('live-output').textContent = JSON.stringify({
          active_notes: liveState.active_notes,
          midi_backend: liveState.settings.midi.backend,
          midi_in: liveState.settings.midi.input_port_name,
          calibration_active: calibration.active,
          awaiting_note: calibration.awaiting_note
        }, null, 2);
        document.getElementById('keymap-output').textContent = JSON.stringify(keymap, null, 2);
        document.getElementById('calibration-output').textContent = JSON.stringify(calibration, null, 2);
      }

      function showResponse(payload) {
        document.getElementById('response-output').textContent = JSON.stringify(payload, null, 2);
      }

      async function runAction(action) {
        try {
          const payload = await action();
          showResponse(payload);
          await refreshState();
        } catch (error) {
          showResponse({error: String(error)});
        }
      }

      async function generateKeymap() {
        await runAction(() => fetchJson('/api/keymap/generate', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            total_leds: Number(document.getElementById('total-leds').value),
            first_led: Number(document.getElementById('first-led').value),
            direction: document.getElementById('direction').value
          })
        }));
      }

      async function startCalibration() {
        await runAction(() => fetchJson('/api/calibration/start', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: '{}'
        }));
      }

      async function armNextKey() {
        await runAction(() => fetchJson('/api/calibration/arm', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: '{}'
        }));
      }

      async function selectKey() {
        await runAction(() => fetchJson('/api/calibration/select', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({note: Number(document.getElementById('selected-note').value)})
        }));
      }

      async function shiftLed(delta) {
        await runAction(() => fetchJson('/api/calibration/shift', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({delta})
        }));
      }

      async function confirmKey() {
        await runAction(() => fetchJson('/api/calibration/confirm', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({note: Number(document.getElementById('selected-note').value)})
        }));
      }

      refreshState();
      setInterval(refreshState, 750);
    </script>
  </body>
</html>
"""


def _json_response(start_response, payload: dict, status: str = "200 OK"):
    """Build a JSON WSGI response."""
    body = json.dumps(payload).encode("utf-8")
    start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(body)))])
    return [body]


def _html_response(start_response, body: str):
    """Build an HTML WSGI response."""
    payload = body.encode("utf-8")
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(payload)))])
    return [payload]


def create_web_app(runtime: PianoLedRuntime):
    """Create the WSGI application bound to a specific runtime instance."""
    def application(environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")
        length = int(environ.get("CONTENT_LENGTH", "0") or "0")
        raw_body = environ["wsgi.input"].read(length) if length else b""
        body = json.loads(raw_body.decode("utf-8")) if raw_body else {}

        if method == "GET" and path == "/keymap":
            return _html_response(start_response, KEYMAP_HTML)

        if method == "GET" and path in {"/", "/settings", "/songs", "/practice"}:
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

        if method == "GET" and path == "/api/keymap":
            return _json_response(start_response, runtime.get_keymap_state())

        if method == "POST" and path == "/api/calibration/start":
            session = runtime.start_calibration()
            return _json_response(start_response, runtime.get_calibration_state() | {"session": session})

        if method == "GET" and path == "/api/calibration/state":
            return _json_response(start_response, runtime.get_calibration_state())

        if method == "POST" and path == "/api/calibration/arm":
            return _json_response(start_response, runtime.arm_calibration_note_capture())

        if method == "POST" and path == "/api/calibration/select":
            session = runtime.calibration_select_key(int(body["note"]))
            return _json_response(start_response, runtime.get_calibration_state() | {"session": session})

        if method == "POST" and path == "/api/calibration/shift":
            session = runtime.calibration_shift(int(body["delta"]))
            return _json_response(start_response, runtime.get_calibration_state() | {"session": session})

        if method == "POST" and path == "/api/calibration/confirm":
            session = runtime.calibration_confirm(int(body["note"]))
            return _json_response(start_response, runtime.get_calibration_state() | {"session": session})

        if method == "GET" and path == "/health":
            return _json_response(start_response, {"status": "ok"})

        return _json_response(start_response, {"error": "not_found", "path": path}, status="404 Not Found")

    return application
