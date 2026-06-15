"""Web server tests for keymap, calibration, and runtime-facing browser APIs."""

import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

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
    def _build_test_application(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        settings_dir = root / "data" / "settings"
        keymaps_dir = root / "data" / "keymaps"
        settings_dir.mkdir(parents=True, exist_ok=True)
        keymaps_dir.mkdir(parents=True, exist_ok=True)
        settings_dir.joinpath("settings.json").write_text(
            json.dumps(
                {
                    "led": {
                        "total_leds": 176,
                        "leds_per_meter": 144,
                        "note_color": "#00b894",
                        "black_key_color": "#0984e3",
                        "use_black_key_color": True,
                        "strip_direction": "right_to_left",
                        "default_first_led": 175,
                        "backend": "fake",
                        "gpio_pin": 18,
                        "brightness": 128,
                        "dma_channel": 10,
                        "pwm_frequency_hz": 800000,
                        "invert_signal": False,
                        "channel": 0,
                    },
                    "midi": {"backend": "fake", "input_port_name": "", "output_port_name": ""},
                    "selected_keymap": "default_88.json",
                }
            ),
            encoding="utf-8",
        )
        keymaps_dir.joinpath("default_88.json").write_text(
            json.dumps({"note_to_led": {"60": 97, "61": 95, "62": 93}}),
            encoding="utf-8",
        )
        return build_application(project_root=root)

    def test_web_app_exposes_runtime_state_and_clear_action(self) -> None:
        application = self._build_test_application()
        app = create_web_app(application.runtime)

        status, headers, payload = _invoke(app, "GET", "/api/state")
        state = json.loads(payload.decode("utf-8"))
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertGreaterEqual(state["settings"]["led"]["total_leds"], 88)

        application.runtime.handle_chase_step()
        status, _, _ = _invoke(app, "POST", "/api/led/clear", b"{}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(application.runtime.led_driver.pixels[0], (0, 0, 0))

    def test_keymap_page_and_api_expose_generation_and_calibration_state(self) -> None:
        application = self._build_test_application()
        app = create_web_app(application.runtime)

        status, headers, payload = _invoke(app, "GET", "/keymap")
        html = payload.decode("utf-8")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("Generate Base Keymap", html)
        self.assertIn("Calibration Controls", html)
        self.assertIn("right_to_left", html)
        self.assertIn("What to Expect", html)
        self.assertIn("Last Response", html)
        self.assertIn("Clear Strip", html)
        self.assertIn("Download Keymap", html)
        self.assertNotIn("Use Next Piano Key", html)
        self.assertIn("Stop Calibration", html)
        self.assertIn("Live Runtime", html)
        self.assertIn("Preview Full Map", html)
        self.assertIn("Shift Whole Map Left on Piano", html)
        self.assertIn("Shift Whole Map Right on Piano", html)
        self.assertIn("Full Keyboard Preview During Calibration", html)
        self.assertIn("Shift Left on Piano", html)
        self.assertIn("Shift Right on Piano", html)
        self.assertIn("document.getElementById('full-preview-toggle').addEventListener('change'", html)
        self.assertIn("cache: 'no-store'", html)
        self.assertIn("last_note_event", html)

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

        status, _, payload = _invoke(app, "POST", "/api/calibration/arm", b"{}")
        calibration_state = json.loads(payload.decode("utf-8"))
        self.assertTrue(calibration_state["awaiting_note"])

        status, _, payload = _invoke(app, "POST", "/api/calibration/stop", b"{}")
        calibration_state = json.loads(payload.decode("utf-8"))
        self.assertFalse(calibration_state["active"])

    def test_settings_page_exposes_led_color_and_brightness_controls(self) -> None:
        application = self._build_test_application()
        app = create_web_app(application.runtime)

        status, headers, payload = _invoke(app, "GET", "/settings")
        html = payload.decode("utf-8")

        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("LED Settings", html)
        self.assertIn("Note Color", html)
        self.assertIn("Black Key Color", html)
        self.assertIn("Use Different Black Key Color", html)
        self.assertIn("Brightness", html)
        self.assertIn("Save Settings", html)

    def test_keymap_download_endpoint_returns_json_attachment(self) -> None:
        application = self._build_test_application()
        app = create_web_app(application.runtime)

        status, headers, payload = _invoke(app, "GET", "/api/keymap/download")
        keymap_state = json.loads(payload.decode("utf-8"))

        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertIn("attachment;", headers["Content-Disposition"])
        self.assertIn("note_to_led", keymap_state)

    def test_keymap_preview_and_whole_map_shift_actions_are_exposed(self) -> None:
        application = self._build_test_application()
        app = create_web_app(application.runtime)

        status, _, payload = _invoke(app, "POST", "/api/keymap/preview", b"{}")
        preview_state = json.loads(payload.decode("utf-8"))
        self.assertEqual(status, "200 OK")
        self.assertTrue(preview_state["full_map_preview_active"])

        status, _, payload = _invoke(app, "POST", "/api/keymap/shift", b'{"direction": "left"}')
        keymap_state = json.loads(payload.decode("utf-8"))
        self.assertEqual(status, "200 OK")
        self.assertIn("note_to_led", keymap_state)

        status, _, payload = _invoke(app, "POST", "/api/calibration/display-mode", b'{"show_full_keyboard_preview": true}')
        calibration_state = json.loads(payload.decode("utf-8"))
        self.assertEqual(status, "200 OK")
        self.assertTrue(calibration_state["show_full_keyboard_preview"])

    def test_calibration_shift_api_accepts_piano_direction(self) -> None:
        application = self._build_test_application()
        app = create_web_app(application.runtime)

        _invoke(app, "POST", "/api/calibration/start", b"{}")
        _invoke(app, "POST", "/api/calibration/select", b'{"note": 60}')
        status, _, payload = _invoke(app, "POST", "/api/calibration/shift", b'{"direction": "left"}')
        calibration_state = json.loads(payload.decode("utf-8"))

        self.assertEqual(status, "200 OK")
        self.assertEqual(calibration_state["session"]["selected_note"], 60)

    def test_settings_api_can_flip_strip_direction(self) -> None:
        application = self._build_test_application()
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

    def test_songs_and_practice_share_the_selected_song(self) -> None:
        application = self._build_test_application()
        songs_dir = application.settings_store.path.parent.parent / "songs" / "midi"
        songs_dir.mkdir(parents=True, exist_ok=True)
        songs_dir.joinpath("Moonlight.mid").write_bytes(b"mid")
        application = build_application(project_root=application.settings_store.path.parent.parent.parent)
        app = create_web_app(application.runtime)

        status, headers, payload = _invoke(app, "GET", "/songs")
        html = payload.decode("utf-8")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("Song Selection", html)

        status, _, payload = _invoke(app, "GET", "/api/songs")
        songs_payload = json.loads(payload.decode("utf-8"))
        self.assertEqual([song["relative_path"] for song in songs_payload["songs"]], ["Moonlight.mid"])

        status, _, payload = _invoke(app, "POST", "/api/song-selection", b'{"relative_path": "Moonlight.mid"}')
        selection_payload = json.loads(payload.decode("utf-8"))
        self.assertEqual(selection_payload["selected_song_path"], "Moonlight.mid")

        status, _, payload = _invoke(app, "GET", "/api/song-selection")
        current_payload = json.loads(payload.decode("utf-8"))
        self.assertEqual(current_payload["selected_song"]["display_title"], "Moonlight")

        status, _, payload = _invoke(app, "GET", "/practice")
        practice_html = payload.decode("utf-8")
        self.assertIn("Learning Mode", practice_html)
        self.assertIn("selected-song-output", practice_html)
