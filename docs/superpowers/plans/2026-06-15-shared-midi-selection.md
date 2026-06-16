# Shared MIDI Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared, session-only MIDI file selection so choosing a song on `/songs` automatically carries over to `/practice`.

**Architecture:** Add a focused `SongLibrary` that scans `data/songs/midi`, then store a single `selected_song_path` in `PianoLedRuntime` as the app-wide source of truth. Expose that state through small JSON APIs and lightweight `/songs` and `/practice` pages so later playback work can plug into the same selected song without redesign.

**Tech Stack:** Python 3.11, `pathlib`, `dataclasses`, stdlib `unittest`, existing WSGI web server

---

## File Structure

### New files

- `src/piano_led/songs/__init__.py`
  - Package marker and public exports for song-library types.
- `src/piano_led/songs/library.py`
  - MIDI folder scanner plus song-entry model.
- `tests/songs/__init__.py`
  - Test package marker.
- `tests/songs/test_library.py`
  - Unit tests for MIDI discovery and metadata shaping.

### Modified files

- `src/piano_led/app.py`
  - Build the song library from `data/songs/midi` and inject it into runtime.
- `src/piano_led/services/runtime.py`
  - Hold `selected_song_path`, validate selections, expose song state to the UI snapshot.
- `src/piano_led/web/server.py`
  - Add `/songs` and `/practice` pages plus song list/selection APIs.
- `tests/services/test_runtime.py`
  - Runtime tests for valid and invalid shared song selection behavior.
- `tests/web/test_server.py`
  - Web/API tests proving `/songs` and `/practice` share the same selected MIDI file.
- `docs/stages/stage-05-midi-playback.md`
  - Note that the first playback slice now includes shared song selection.

---

### Task 1: Add The Song Library

**Files:**
- Create: `src/piano_led/songs/__init__.py`
- Create: `src/piano_led/songs/library.py`
- Create: `tests/songs/__init__.py`
- Create: `tests/songs/test_library.py`

- [ ] **Step 1: Write the failing library tests**

```python
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
            root.joinpath("alpha.mid").write_bytes(b"mid")
            root.joinpath("beta.midi").write_bytes(b"midi")
            root.joinpath("ignore.txt").write_text("nope", encoding="utf-8")

            songs = SongLibrary(root).list_songs()

            self.assertEqual(
                [song["relative_path"] for song in songs],
                ["alpha.mid", "beta.midi"],
            )

    def test_list_songs_builds_stable_display_titles(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath("Ludwig van Beethoven - Fur Elise.mid").write_bytes(b"mid")

            songs = SongLibrary(root).list_songs()

            self.assertEqual(songs[0]["file_name"], "Ludwig van Beethoven - Fur Elise.mid")
            self.assertEqual(songs[0]["display_title"], "Ludwig van Beethoven - Fur Elise")
```

- [ ] **Step 2: Run the library tests to verify they fail**

Run:

```bash
python3 -m unittest tests.songs.test_library -v
```

Expected:

```text
ModuleNotFoundError: No module named 'piano_led.songs'
```

- [ ] **Step 3: Write the minimal song library implementation**

`src/piano_led/songs/library.py`

```python
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
        if not self.midi_root.exists():
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
```

`src/piano_led/songs/__init__.py`

```python
"""Song-library helpers for MIDI browsing and later playback stages."""

from piano_led.songs.library import SongEntry, SongLibrary

__all__ = ["SongEntry", "SongLibrary"]
```

`tests/songs/__init__.py`

```python
"""Tests for the song library and later playback helpers."""
```

- [ ] **Step 4: Run the library tests to verify they pass**

Run:

```bash
python3 -m unittest tests.songs.test_library -v
```

Expected:

```text
test_list_songs_builds_stable_display_titles ... ok
test_list_songs_only_returns_mid_and_midi_files ... ok
```

- [ ] **Step 5: Commit the song library**

```bash
git add -- src/piano_led/songs/__init__.py src/piano_led/songs/library.py tests/songs/__init__.py tests/songs/test_library.py
git commit -m "feat: add midi song library"
```

---

### Task 2: Add Shared Runtime Song Selection

**Files:**
- Modify: `src/piano_led/app.py`
- Modify: `src/piano_led/services/runtime.py`
- Modify: `tests/services/test_runtime.py`

- [ ] **Step 1: Write the failing runtime tests**

Add these tests to `tests/services/test_runtime.py`:

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from piano_led.songs.library import SongLibrary
```

```python
    def test_runtime_can_select_a_valid_song_from_library(self) -> None:
        settings = AppSettings(led=LedSettings(total_leds=8))
        driver = FakeLedDriver(total_leds=8)
        with TemporaryDirectory() as tmp:
            midi_root = Path(tmp)
            midi_root.joinpath("etude.mid").write_bytes(b"mid")
            runtime = PianoLedRuntime(
                settings=settings,
                keymap=Keymap(note_to_led={60: 1}),
                led_driver=driver,
                song_library=SongLibrary(midi_root),
            )

            selection = runtime.select_song("etude.mid")

            self.assertEqual(selection["selected_song_path"], "etude.mid")
            self.assertEqual(selection["selected_song"]["display_title"], "etude")

    def test_runtime_rejects_unknown_song_selection(self) -> None:
        settings = AppSettings(led=LedSettings(total_leds=8))
        driver = FakeLedDriver(total_leds=8)
        with TemporaryDirectory() as tmp:
            runtime = PianoLedRuntime(
                settings=settings,
                keymap=Keymap(note_to_led={60: 1}),
                led_driver=driver,
                song_library=SongLibrary(Path(tmp)),
            )

            with self.assertRaises(ValueError):
                runtime.select_song("missing.mid")
```

- [ ] **Step 2: Run the runtime tests to verify they fail**

Run:

```bash
python3 -m unittest tests.services.test_runtime -v
```

Expected:

```text
TypeError: PianoLedRuntime.__init__() got an unexpected keyword argument 'song_library'
```

- [ ] **Step 3: Write the minimal runtime implementation**

Update `src/piano_led/services/runtime.py` imports:

```python
from piano_led.songs.library import SongLibrary
```

Update the initializer signature and fields:

```python
        state_store: StateStore | None = None,
        song_library: SongLibrary | None = None,
    ) -> None:
```

```python
        self.song_library = song_library
        self.selected_song_path: str | None = None
```

Add these methods to `PianoLedRuntime`:

```python
    def list_songs(self) -> list[dict]:
        """Return the currently available MIDI songs."""

        if self.song_library is None:
            return []
        return self.song_library.list_songs()

    def get_selected_song(self) -> dict | None:
        """Return metadata for the currently selected song, if any."""

        if self.selected_song_path is None:
            return None
        for song in self.list_songs():
            if song["relative_path"] == self.selected_song_path:
                return song
        self.selected_song_path = None
        return None

    def get_song_selection_state(self) -> dict:
        """Return the available songs plus the current selection."""

        return {
            "songs": self.list_songs(),
            "selected_song_path": self.selected_song_path,
            "selected_song": self.get_selected_song(),
        }

    def select_song(self, relative_path: str) -> dict:
        """Select a MIDI file from the current song library."""

        for song in self.list_songs():
            if song["relative_path"] == relative_path:
                self.selected_song_path = relative_path
                self.refresh_state()
                return self.get_song_selection_state()
        raise ValueError(f"Unknown song selection: {relative_path}")
```

Update `refresh_state()`:

```python
            songs=self.list_songs(),
            selected_song_path=self.selected_song_path,
            selected_song=self.get_selected_song(),
```

Update `src/piano_led/app.py` imports:

```python
from piano_led.songs.library import SongLibrary
```

Build and pass the library in `build_application()`:

```python
    songs_root = root / "data" / "songs" / "midi"
```

```python
    song_library = SongLibrary(songs_root)
```

```python
        state_store=state_store,
        song_library=song_library,
```

- [ ] **Step 4: Run the runtime tests to verify they pass**

Run:

```bash
python3 -m unittest tests.services.test_runtime -v
```

Expected:

```text
test_runtime_can_select_a_valid_song_from_library ... ok
test_runtime_rejects_unknown_song_selection ... ok
```

- [ ] **Step 5: Commit the runtime selection state**

```bash
git add -- src/piano_led/app.py src/piano_led/services/runtime.py tests/services/test_runtime.py
git commit -m "feat: add shared runtime song selection"
```

---

### Task 3: Add Song Selection APIs And Pages

**Files:**
- Modify: `src/piano_led/web/server.py`
- Modify: `tests/web/test_server.py`

- [ ] **Step 1: Write the failing web tests**

Add this test to `tests/web/test_server.py`:

```python
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
```

- [ ] **Step 2: Run the web tests to verify they fail**

Run:

```bash
python3 -m unittest tests.web.test_server -v
```

Expected:

```text
AssertionError: 'Song Selection' not found
```

- [ ] **Step 3: Write the minimal web implementation**

Replace the placeholder `/songs` and `/practice` HTML with focused pages in `src/piano_led/web/server.py`.

Add:

```python
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
        <select id="song-select"></select>
        <button onclick="saveSongSelection()">Use This Song</button>
      </section>
      <section class="panel">
        <h2>Current Selection</h2>
        <pre id="song-selection-output">Loading...</pre>
      </section>
    </div>
    <script>
      async function fetchJson(url, options) {
        const response = await fetch(url, {...(options || {}), cache: 'no-store'});
        return await response.json();
      }

      async function refreshSongs() {
        const songsPayload = await fetchJson('/api/songs');
        const selectionPayload = await fetchJson('/api/song-selection');
        const select = document.getElementById('song-select');
        select.innerHTML = '';
        for (const song of songsPayload.songs) {
          const option = document.createElement('option');
          option.value = song.relative_path;
          option.textContent = song.display_title;
          if (selectionPayload.selected_song_path === song.relative_path) {
            option.selected = true;
          }
          select.appendChild(option);
        }
        document.getElementById('song-selection-output').textContent = JSON.stringify(selectionPayload, null, 2);
      }

      async function saveSongSelection() {
        await fetchJson('/api/song-selection', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({relative_path: document.getElementById('song-select').value})
        });
        await refreshSongs();
      }

      refreshSongs();
      setInterval(refreshSongs, 1000);
    </script>
  </body>
</html>
"""
```

Add:

```python
PRACTICE_HTML = """<!doctype html>
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
        <pre id="selected-song-output">Loading...</pre>
      </section>
    </div>
    <script>
      async function fetchJson(url, options) {
        const response = await fetch(url, {...(options || {}), cache: 'no-store'});
        return await response.json();
      }

      async function refreshPractice() {
        const selectionPayload = await fetchJson('/api/song-selection');
        document.getElementById('selected-song-output').textContent = JSON.stringify(selectionPayload, null, 2);
      }

      refreshPractice();
      setInterval(refreshPractice, 1000);
    </script>
  </body>
</html>
"""
```

Update routing:

```python
        if method == "GET" and path == "/songs":
            return _html_response(start_response, SONGS_HTML)

        if method == "GET" and path == "/practice":
            return _html_response(start_response, PRACTICE_HTML)

        if method == "GET" and path == "/":
            return _html_response(start_response, INDEX_HTML)
```

Add APIs:

```python
        if method == "GET" and path == "/api/songs":
            return _json_response(start_response, {"songs": runtime.list_songs()})

        if method == "GET" and path == "/api/song-selection":
            return _json_response(start_response, runtime.get_song_selection_state())

        if method == "POST" and path == "/api/song-selection":
            try:
                payload = runtime.select_song(str(body["relative_path"]))
            except ValueError as error:
                return _json_response(start_response, {"error": str(error)}, status="400 Bad Request")
            return _json_response(start_response, payload)
```

- [ ] **Step 4: Run the web tests to verify they pass**

Run:

```bash
python3 -m unittest tests.web.test_server -v
```

Expected:

```text
test_songs_and_practice_share_the_selected_song ... ok
```

- [ ] **Step 5: Commit the web song-selection flow**

```bash
git add -- src/piano_led/web/server.py tests/web/test_server.py
git commit -m "feat: add shared web midi selection"
```

---

### Task 4: Update Stage Documentation And Full Verification

**Files:**
- Modify: `docs/stages/stage-05-midi-playback.md`

- [ ] **Step 1: Update the stage document**

Add this section to `docs/stages/stage-05-midi-playback.md`:

```markdown
## First implemented slice

- shared MIDI song discovery from `data/songs/midi`
- one runtime-wide selected MIDI file
- `/songs` picker and `/practice` shared selection display
- session-only selection state for the current app run
```

- [ ] **Step 2: Run the focused test commands**

Run:

```bash
python3 -m unittest tests.songs.test_library tests.services.test_runtime tests.web.test_server -v
```

Expected:

```text
... ok
... ok
... ok
```

- [ ] **Step 3: Run the full suite**

Run:

```bash
python3 -m unittest discover -s tests -t . -v
```

Expected:

```text
Ran ... tests in ...s

OK
```

- [ ] **Step 4: Commit the docs and verification-ready state**

```bash
git add -- docs/stages/stage-05-midi-playback.md
git commit -m "docs: note shared midi selection stage progress"
```

---

## Spec Coverage Check

- Song-library scan from `data/songs/midi`: covered by Task 1
- Shared runtime-wide selected MIDI file: covered by Task 2
- `/songs` can view and change selection: covered by Task 3
- `/practice` shows the same selected file: covered by Task 3
- Session-only behavior: covered by Task 2 and verified by omission from settings writes
- Keep selection out of persisted settings: covered by Task 2 tests and no settings-store write path
- Friendly first Stage 5 slice without playback engine: covered by Tasks 2-4

## Self-Review

- No placeholder steps remain.
- Method names are consistent across tasks: `list_songs`, `select_song`, `get_song_selection_state`.
- The plan stays within the approved scope and does not pull in MIDI parsing or transport work early.

## Pi Test Checklist

After implementation on the Pi:

1. Put one or more `.mid` files in `data/songs/midi`.
2. Run the test suite.
3. Start the web server with live mode if desired.
4. Open `/songs` on your PC or tablet.
5. Select a MIDI file and click `Use This Song`.
6. Open `/practice`.
7. Confirm the same selected file is already shown there.
8. Restart the app and confirm the selection resets, since this slice is session-only.
