"""Per-song hand assignment metadata stored beside MIDI library data."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class SongHandConfig:
    """Manual left/right hand assignment for one MIDI song."""

    relative_path: str
    left_hand_tracks: list[int] = field(default_factory=list)
    right_hand_tracks: list[int] = field(default_factory=list)
    left_hand_channels: list[int] = field(default_factory=list)
    right_hand_channels: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return a plain dictionary for storage and API responses."""

        return asdict(self)


class SongHandConfigStore:
    """Load and save hand setup JSON files for each MIDI song."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path_for_song(self, relative_path: str) -> Path:
        """Return the metadata path for one relative MIDI file path."""

        safe_name = Path(relative_path).with_suffix(".json").name
        return self.root / safe_name

    def load(self, relative_path: str) -> SongHandConfig:
        """Load a saved hand configuration or return an empty default."""

        path = self._path_for_song(relative_path)
        if not path.exists():
            return SongHandConfig(relative_path=relative_path)
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return SongHandConfig(
            relative_path=payload.get("relative_path", relative_path),
            left_hand_tracks=[int(value) for value in payload.get("left_hand_tracks", [])],
            right_hand_tracks=[int(value) for value in payload.get("right_hand_tracks", [])],
            left_hand_channels=[int(value) for value in payload.get("left_hand_channels", [])],
            right_hand_channels=[int(value) for value in payload.get("right_hand_channels", [])],
        )

    def save(self, config: SongHandConfig) -> SongHandConfig:
        """Persist one song hand configuration to disk."""

        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path_for_song(config.relative_path)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(config.to_dict(), handle, indent=2)
        return config
