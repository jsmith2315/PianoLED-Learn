"""Minimal WSGI app for the tablet/browser control surface."""

from __future__ import annotations

import html
import json

from piano_led.services.runtime import PianoLedRuntime


BASE_STYLE = """
      body { font-family: Georgia, serif; margin: 2rem; background: linear-gradient(120deg, #f4efe6, #dfe9f3); color: #1f2a37; }
      nav a { margin-right: 1rem; color: #0f4c81; text-decoration: none; font-weight: bold; }
      .card { background: rgba(255,255,255,0.85); padding: 1rem 1.25rem; border-radius: 16px; max-width: 60rem; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }
      .grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }
      .panel { background: #ffffffcc; padding: 1rem; border-radius: 14px; }
      button { background: #0f4c81; color: white; border: 0; border-radius: 999px; padding: 0.6rem 1rem; cursor: pointer; }
      .button-link { display: inline-block; background: #0f4c81; color: white; text-decoration: none; border-radius: 999px; padding: 0.6rem 1rem; }
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

SETTINGS_HTML = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Piano LED Learn - Settings</title>
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
      <h1>LED Settings</h1>
      <p>Adjust core LED colors and strip brightness without editing JSON by hand.</p>
      <div class="grid">
        <section class="panel">
          <label>Note Color</label>
          <input id="note-color" type="color" value="#00b894">
          <label>Black Key Color</label>
          <input id="black-key-color" type="color" value="#0984e3">
          <label><input id="use-black-key-color" type="checkbox"> Use Different Black Key Color</label>
          <label>Brightness</label>
          <input id="brightness" type="range" min="0" max="255" value="128">
          <div>Brightness Value: <span id="brightness-value">128</span></div>
          <button onclick="saveSettings()">Save Settings</button>
        </section>
        <section class="panel">
          <h2>Last Response</h2>
          <pre id="settings-response">No changes yet.</pre>
        </section>
      </div>
    </div>
    <script>
      async function fetchJson(url, options) {
        const response = await fetch(url, {...(options || {}), cache: 'no-store'});
        return await response.json();
      }

      function showResponse(payload) {
        document.getElementById('settings-response').textContent = JSON.stringify(payload, null, 2);
      }

      async function refreshSettings() {
        const settings = await fetchJson('/api/settings');
        document.getElementById('note-color').value = settings.led.note_color;
        document.getElementById('black-key-color').value = settings.led.black_key_color;
        document.getElementById('use-black-key-color').checked = settings.led.use_black_key_color;
        document.getElementById('brightness').value = settings.led.brightness;
        document.getElementById('brightness-value').textContent = settings.led.brightness;
      }

      async function saveSettings() {
        const payload = await fetchJson('/api/settings', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            led: {
              note_color: document.getElementById('note-color').value,
              black_key_color: document.getElementById('black-key-color').value,
              use_black_key_color: document.getElementById('use-black-key-color').checked,
              brightness: Number(document.getElementById('brightness').value)
            }
          })
        });
        showResponse(payload);
        await refreshSettings();
      }

      document.getElementById('brightness').addEventListener('input', (event) => {
        document.getElementById('brightness-value').textContent = event.target.value;
      });

      refreshSettings();
    </script>
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
          <button onclick="previewFullMap()">Preview Full Map</button>
          <button onclick="shiftWholeMap('left')">Shift Whole Map Left on Piano</button>
          <button onclick="shiftWholeMap('right')">Shift Whole Map Right on Piano</button>
          <button onclick="clearStrip()">Clear Strip</button>
          <a class="button-link" href="/api/keymap/download">Download Keymap</a>
        </section>
        <section class="panel">
          <h2>Calibration Controls</h2>
          <label>Selected Note</label>
          <input id="selected-note" type="number" value="60">
          <label><input id="full-preview-toggle" type="checkbox"> Full Keyboard Preview During Calibration</label>
          <button onclick="startCalibration()">Start Calibration</button>
          <button onclick="stopCalibration()">Stop Calibration</button>
          <button onclick="selectKey()">Select Key</button>
          <button onclick="shiftLed('left')">Shift Left on Piano</button>
          <button onclick="shiftLed('right')">Shift Right on Piano</button>
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
        <p>Preview Full Map lights the current keymap using note color for white keys and black-key color for black keys, so you can shift the whole map closer before fine tuning.</p>
        <p>Start Calibration immediately listens for piano keys. Turn on full-keyboard preview if you want every mapped note lit between edits.</p>
        <p>When no note is selected, press a piano key to choose it and light its current LED. Once a note is selected, pressing any lower piano key nudges that LED one step left, and pressing any higher piano key nudges it one step right.</p>
        <p>Press the selected piano key again to save that mapping. If full-keyboard preview is enabled, the whole keyboard comes back after each confirm.</p>
        <p>Shift Left on Piano and Shift Right on Piano follow the physical piano direction even when the strip starts on the right side.</p>
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
        const response = await fetch(url, {...(options || {}), cache: 'no-store'});
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
        document.getElementById('full-preview-toggle').checked = calibration.show_full_keyboard_preview;
        document.getElementById('live-output').textContent = JSON.stringify({
          active_notes: liveState.active_notes,
          last_note_event: liveState.last_note_event,
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

      async function previewFullMap() {
        await runAction(() => fetchJson('/api/keymap/preview', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: '{}'
        }));
      }

      async function shiftWholeMap(direction) {
        await runAction(() => fetchJson('/api/keymap/shift', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({direction})
        }));
      }

      async function clearStrip() {
        await runAction(() => fetchJson('/api/led/clear', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: '{}'
        }));
      }

      async function setCalibrationDisplayMode() {
        return await fetchJson('/api/calibration/display-mode', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            show_full_keyboard_preview: document.getElementById('full-preview-toggle').checked
          })
        });
      }

      async function startCalibration() {
        await setCalibrationDisplayMode();
        await runAction(() => fetchJson('/api/calibration/start', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: '{}'
        }));
      }

      async function stopCalibration() {
        await runAction(() => fetchJson('/api/calibration/stop', {
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

      async function shiftLed(direction) {
        await runAction(() => fetchJson('/api/calibration/shift', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({direction})
        }));
      }

      async function confirmKey() {
        await runAction(() => fetchJson('/api/calibration/confirm', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({note: Number(document.getElementById('selected-note').value)})
        }));
      }

      document.getElementById('full-preview-toggle').addEventListener('change', () => {
        runAction(() => setCalibrationDisplayMode());
      });

      refreshState();
      setInterval(refreshState, 750);
    </script>
  </body>
</html>
"""


SONGS_HTML = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Piano LED Learn - Songs</title>
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
      <h1>Song Selection</h1>
      <p>Choose a MIDI file here once, and the current learning page will use the same selection.</p>
      <section class="panel">
        <label>Available MIDI Files</label>
        <p id="songs-empty-state">No MIDI files found in data/songs/midi yet.</p>
        <select id="song-select" hidden disabled>
          <option value="" selected>Choose a song...</option>
        </select>
        <button id="song-select-button" onclick="saveSongSelection()" hidden disabled>Use This Song</button>
      </section>
      <section class="panel">
        <h2>Current Selection</h2>
        <pre id="song-selection-output">No song selected yet.</pre>
      </section>
    </div>
    <script>
      async function fetchJson(url, options) {
        const response = await fetch(url, {...(options || {}), cache: 'no-store'});
        return await response.json();
      }

      function updateSongSelectionButton() {
        const select = document.getElementById('song-select');
        const button = document.getElementById('song-select-button');
        button.disabled = !select.value;
      }

      async function refreshSongs() {
        const songsPayload = await fetchJson('/api/songs');
        const selectionPayload = await fetchJson('/api/song-selection');
        const emptyState = document.getElementById('songs-empty-state');
        const select = document.getElementById('song-select');
        const button = document.getElementById('song-select-button');
        const output = document.getElementById('song-selection-output');
        const pendingValue = select.value;
        const hasPendingSelection = pendingValue && pendingValue !== selectionPayload.selected_song_path;
        const effectiveSelectedPath = hasPendingSelection ? pendingValue : selectionPayload.selected_song_path;
        select.innerHTML = '';
        if (!songsPayload.songs.length) {
          emptyState.hidden = false;
          select.hidden = true;
          select.disabled = true;
          button.hidden = true;
          button.disabled = true;
          output.textContent = 'No MIDI files found in data/songs/midi yet.';
          return;
        }
        emptyState.hidden = true;
        select.hidden = false;
        select.disabled = false;
        button.hidden = false;
        if (!songsPayload.songs.some(song => song.relative_path === effectiveSelectedPath)) {
          const placeholder = document.createElement('option');
          placeholder.value = '';
          placeholder.textContent = 'Choose a song...';
          placeholder.disabled = true;
          placeholder.selected = true;
          select.appendChild(placeholder);
        }
        for (const song of songsPayload.songs) {
          const option = document.createElement('option');
          option.value = song.relative_path;
          option.textContent = song.display_title;
          if (effectiveSelectedPath === song.relative_path) {
            option.selected = true;
          }
          select.appendChild(option);
        }
        updateSongSelectionButton();
        if (!selectionPayload.selected_song) {
          output.textContent = 'No song selected yet.';
          return;
        }
        output.textContent = JSON.stringify(selectionPayload, null, 2);
      }

      async function saveSongSelection() {
        await fetchJson('/api/song-selection', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({relative_path: document.getElementById('song-select').value})
        });
        await refreshSongs();
      }

      document.getElementById('song-select').addEventListener('change', updateSongSelectionButton);
      refreshSongs();
      setInterval(refreshSongs, 1000);
    </script>
  </body>
</html>
"""


def _practice_html(runtime: PianoLedRuntime) -> str:
    """Build the practice page with the current selection visible on first load."""

    selection_payload = runtime.get_song_selection_state()
    if not selection_payload["songs"]:
        empty_state = "No MIDI files found in data/songs/midi yet."
        empty_hidden = ""
        output_hidden = " hidden"
        output_text = ""
    elif selection_payload["selected_song"] is None:
        empty_state = "No song selected yet. Choose a MIDI file on the Songs page to begin practicing."
        empty_hidden = ""
        output_hidden = " hidden"
        output_text = ""
    else:
        empty_state = ""
        empty_hidden = " hidden"
        output_hidden = ""
        output_text = html.escape(json.dumps(selection_payload, indent=2))

    return """<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Piano LED Learn - Practice</title>
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
      <h1>Learning Mode</h1>
      <p>This page will host practice playback next. For now, it reads the shared song selection from the runtime.</p>
      <section class="panel">
        <h2>Selected Song</h2>
""" + '<p id="practice-empty-state"' + empty_hidden + ">" + html.escape(empty_state) + "</p>" + """
""" + '<pre id="selected-song-output"' + output_hidden + ">" + output_text + "</pre>" + """
      </section>
    </div>
    <script>
      async function fetchJson(url, options) {
        const response = await fetch(url, {...(options || {}), cache: 'no-store'});
        return await response.json();
      }

      async function refreshPractice() {
        const selectionPayload = await fetchJson('/api/song-selection');
        const emptyState = document.getElementById('practice-empty-state');
        const output = document.getElementById('selected-song-output');
        if (!selectionPayload.songs.length) {
          emptyState.hidden = false;
          emptyState.textContent = 'No MIDI files found in data/songs/midi yet.';
          output.hidden = true;
          output.textContent = '';
          return;
        }
        if (!selectionPayload.selected_song) {
          emptyState.hidden = false;
          emptyState.textContent = 'No song selected yet. Choose a MIDI file on the Songs page to begin practicing.';
          output.hidden = true;
          output.textContent = '';
          return;
        }
        emptyState.hidden = true;
        output.hidden = false;
        output.textContent = JSON.stringify(selectionPayload, null, 2);
      }

      refreshPractice();
      setInterval(refreshPractice, 1000);
    </script>
  </body>
</html>
"""


def _json_response(start_response, payload: dict, status: str = "200 OK"):
    """Build a JSON WSGI response."""
    body = json.dumps(payload).encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
        ],
    )
    return [body]


def _html_response(start_response, body: str):
    """Build an HTML WSGI response."""
    payload = body.encode("utf-8")
    start_response(
        "200 OK",
        [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(payload))),
            ("Cache-Control", "no-store"),
        ],
    )
    return [payload]


def _download_response(start_response, payload: dict, filename: str):
    """Build a JSON attachment response for browser downloads."""

    body = json.dumps(payload, indent=2).encode("utf-8")
    start_response(
        "200 OK",
        [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
            ("Content-Disposition", f'attachment; filename="{filename}"'),
            ("Cache-Control", "no-store"),
        ],
    )
    return [body]


def create_web_app(runtime: PianoLedRuntime):
    """Create the WSGI application bound to a specific runtime instance."""
    def application(environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")
        length = int(environ.get("CONTENT_LENGTH", "0") or "0")
        raw_body = environ["wsgi.input"].read(length) if length else b""
        try:
            body = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _json_response(
                start_response,
                {"error": "invalid_json", "message": "Request body must be valid JSON."},
                status="400 Bad Request",
            )

        if method == "GET" and path == "/keymap":
            return _html_response(start_response, KEYMAP_HTML)

        if method == "GET" and path == "/settings":
            return _html_response(start_response, SETTINGS_HTML)

        if method == "GET" and path == "/songs":
            return _html_response(start_response, SONGS_HTML)

        if method == "GET" and path == "/practice":
            return _html_response(start_response, _practice_html(runtime))

        if method == "GET" and path == "/":
            return _html_response(start_response, INDEX_HTML)

        if method == "GET" and path == "/api/state":
            return _json_response(start_response, runtime.get_state())

        if method == "GET" and path == "/api/songs":
            return _json_response(start_response, {"songs": runtime.list_songs()})

        if method == "GET" and path == "/api/song-selection":
            return _json_response(start_response, runtime.get_song_selection_state())

        if method == "POST" and path == "/api/song-selection":
            if not isinstance(body, dict):
                return _json_response(
                    start_response,
                    {"error": "invalid_request", "message": "Request body must be a JSON object."},
                    status="400 Bad Request",
                )
            relative_path = body.get("relative_path")
            if not isinstance(relative_path, str) or not relative_path:
                return _json_response(
                    start_response,
                    {"error": "invalid_request", "message": "Request body must include relative_path."},
                    status="400 Bad Request",
                )
            try:
                payload = runtime.select_song(relative_path)
            except ValueError as error:
                return _json_response(start_response, {"error": str(error)}, status="400 Bad Request")
            return _json_response(start_response, payload)

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

        if method == "POST" and path == "/api/keymap/preview":
            return _json_response(start_response, runtime.preview_full_keymap())

        if method == "POST" and path == "/api/keymap/shift":
            return _json_response(start_response, runtime.shift_full_keymap_piano(str(body["direction"])))

        if method == "GET" and path == "/api/keymap":
            return _json_response(start_response, runtime.get_keymap_state())

        if method == "GET" and path == "/api/keymap/download":
            return _download_response(start_response, runtime.keymap.to_dict(), "piano-led-keymap.json")

        if method == "POST" and path == "/api/calibration/start":
            session = runtime.start_calibration()
            return _json_response(start_response, runtime.get_calibration_state() | {"session": session})

        if method == "GET" and path == "/api/calibration/state":
            return _json_response(start_response, runtime.get_calibration_state())

        if method == "POST" and path == "/api/calibration/arm":
            return _json_response(start_response, runtime.arm_calibration_note_capture())

        if method == "POST" and path == "/api/calibration/display-mode":
            return _json_response(
                start_response,
                runtime.set_calibration_full_preview(bool(body.get("show_full_keyboard_preview"))),
            )

        if method == "POST" and path == "/api/calibration/stop":
            return _json_response(start_response, runtime.stop_calibration())

        if method == "POST" and path == "/api/calibration/select":
            session = runtime.calibration_select_key(int(body["note"]))
            return _json_response(start_response, runtime.get_calibration_state() | {"session": session})

        if method == "POST" and path == "/api/calibration/shift":
            if "direction" in body:
                session = runtime.calibration_shift_piano(str(body["direction"]))
            else:
                session = runtime.calibration_shift(int(body["delta"]))
            return _json_response(start_response, runtime.get_calibration_state() | {"session": session})

        if method == "POST" and path == "/api/calibration/confirm":
            session = runtime.calibration_confirm(int(body["note"]))
            return _json_response(start_response, runtime.get_calibration_state() | {"session": session})

        if method == "GET" and path == "/health":
            return _json_response(start_response, {"status": "ok"})

        return _json_response(start_response, {"error": "not_found", "path": path}, status="404 Not Found")

    return application
