"""Regression checks for FastAPI UI assets and interaction-focused markup."""

from __future__ import annotations

import unittest
from pathlib import Path


class FastApiUiAssetsTest(unittest.TestCase):
    def test_settings_page_uses_scrollable_status_panels(self) -> None:
        template_path = Path("src/piano_led/web/templates/settings.html")
        html = template_path.read_text(encoding="utf-8")

        self.assertIn('class="status-panel rounded-2xl bg-slate-900 p-4 text-sm text-slate-100"', html)
        self.assertIn('class="status-panel text-sm text-slate-800"', html)

    def test_settings_page_pauses_live_polling_while_midi_dropdown_is_active(self) -> None:
        script_path = Path("src/piano_led/web/static/js/settings-page.js")
        script = script_path.read_text(encoding="utf-8")

        self.assertIn("midiSelectFocused: false,", script)
        self.assertIn("if (!this.midiSelectFocused) {", script)
        self.assertIn("@focus=\"midiSelectFocused = true\"", Path("src/piano_led/web/templates/settings.html").read_text(encoding="utf-8"))
        self.assertIn("@blur=\"midiSelectFocused = false\"", Path("src/piano_led/web/templates/settings.html").read_text(encoding="utf-8"))

    def test_shared_status_panel_style_adds_fixed_height_and_scrollbar(self) -> None:
        css_path = Path("src/piano_led/web/static/css/app.css")
        css = css_path.read_text(encoding="utf-8")

        self.assertIn(".status-panel {", css)
        self.assertIn("max-height: 28rem;", css)
        self.assertIn("overflow: auto;", css)


if __name__ == "__main__":
    unittest.main()
