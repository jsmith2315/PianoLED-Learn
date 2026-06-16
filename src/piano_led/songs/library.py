"""Scan the MIDI song directory and return user-facing song entries."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class SongEntry:
    """Simple metadata for a MIDI file available to the web UI."""

    file_name: str
    relative_path: str
    display_title: str

    def to_dict(self) -> dict:
        return asdict(self)


class SongLibrary:
    """Discover MIDI files stored under the configured songs directory."""

    def __init__(self, midi_root: Path) -> None:
        self.midi_root = midi_root

    def list_songs(self) -> list[dict]:
        entries: list[SongEntry] = []
        if not self.midi_root.is_dir():
            return []

        for path in sorted(self.midi_root.iterdir(), key=lambda item: item.name.lower()):
            if path.suffix.lower() not in {".mid", ".midi"} or not path.is_file():
                continue
            entries.append(
                SongEntry(
                    file_name=path.name,
                    relative_path=path.name,
                    display_title=path.stem,
                )
            )
        return [entry.to_dict() for entry in entries]
