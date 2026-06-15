"""Tests for MIDI song discovery and metadata."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from piano_led.songs.library import SongLibrary


class SongLibraryTest(unittest.TestCase):
    def test_list_songs_only_returns_mid_and_midi_files(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath("beta.midi").write_bytes(b"midi")
            root.joinpath("Alpha.mid").write_bytes(b"mid")
            root.joinpath("charlie.MID").write_bytes(b"mid")
            root.joinpath("ignore.txt").write_text("nope", encoding="utf-8")
            nested_dir = root.joinpath("nested")
            nested_dir.mkdir()
            nested_dir.joinpath("delta.mid").write_bytes(b"mid")

            songs = SongLibrary(root).list_songs()

            self.assertEqual(
                [song["relative_path"] for song in songs],
                ["Alpha.mid", "beta.midi", "charlie.MID"],
            )

    def test_list_songs_builds_stable_display_titles(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath("Ludwig van Beethoven - Fur Elise.mid").write_bytes(b"mid")

            songs = SongLibrary(root).list_songs()

            self.assertEqual(songs[0]["file_name"], "Ludwig van Beethoven - Fur Elise.mid")
            self.assertEqual(songs[0]["display_title"], "Ludwig van Beethoven - Fur Elise")
