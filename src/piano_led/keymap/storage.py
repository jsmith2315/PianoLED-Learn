"""JSON persistence helpers for keymap files."""

from __future__ import annotations

import json
from pathlib import Path

from piano_led.keymap.models import Keymap


class KeymapStore:
    """Load and save keymaps from JSON files on disk."""
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> Keymap:
        if not self.path.exists():
            return Keymap()
        with self.path.open("r", encoding="utf-8") as handle:
            return Keymap.from_dict(json.load(handle))

    def save(self, keymap: Keymap) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(keymap.to_dict(), handle, indent=2)
