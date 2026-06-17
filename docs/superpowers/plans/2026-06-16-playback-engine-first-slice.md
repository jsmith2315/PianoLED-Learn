# Playback Engine First Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first usable MIDI playback flow so a song selected on `/songs` can be played from `/practice`, heard on the piano through MIDI output when configured, and shown on the LED strip in sync.

**Architecture:** Add a focused `PlaybackService` owned by `PianoLedRuntime`. The service loads a selected MIDI file into timed note events, runs a background playback thread using `time.monotonic()`, sends note events to LEDs and MIDI output, and exposes compact playback state to the web UI. By user preference, verification is done with manual Pi smoke testing instead of automated unit tests.

**Tech Stack:** Python 3.11, `mido`, background threading, existing WSGI web UI, existing runtime/state store, Raspberry Pi smoke tests

---

## File Structure

- `src/piano_led/core/models.py`
  Add small shared dataclasses for timed playback events and playback state so the runtime, playback service, and web layer use the same shapes.

- `src/piano_led/songs/midi_loader.py`
  New focused MIDI file loader that converts one MIDI file into absolute-timed note events and a duration value.

- `src/piano_led/services/playback.py`
  New playback engine module that owns the worker thread, event scheduling, active playback notes, stop cleanup, and state reporting.

- `src/piano_led/services/runtime.py`
  Wire the playback service into the existing runtime, expose start/stop/get methods, block live LED rendering while playback is active, and publish playback state.

- `src/piano_led/app.py`
  Pass MIDI output into the runtime so playback can sound notes on the piano.

- `src/piano_led/web/server.py`
  Add `/api/playback` endpoints and extend the `/practice` page with `Play Selected Song`, `Stop`, and live playback status.

- `docs/stages/stage-05-midi-playback.md`
  Update the stage document so it reflects that the first real playback slice has been implemented and how it is verified on the Pi.

## Task 1: Add Shared Playback Models

**Files:**
- Modify: `src/piano_led/core/models.py`

- [ ] **Step 1: Extend the shared models module with playback dataclasses**

```python
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class TimedMidiEvent:
    """One note event scheduled at an absolute playback time in seconds."""

    time_seconds: float
    event: NoteEvent


@dataclass(frozen=True)
class LoadedMidiSong:
    """Parsed MIDI song data ready for playback scheduling."""

    relative_path: str
    display_title: str
    duration_seconds: float
    events: list[TimedMidiEvent]


@dataclass
class PlaybackState:
    """Serializable runtime state for the first playback slice."""

    status: str = "stopped"
    selected_song_path: str | None = None
    song_title: str | None = None
    duration_seconds: float = 0.0
    elapsed_seconds: float = 0.0
    active_notes: list[int] = field(default_factory=list)
    midi_output_enabled: bool = False
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)
```

- [ ] **Step 2: Keep the existing `NoteEvent` API unchanged**

```python
@classmethod
def note_on(cls, note: int, velocity: int, source: str) -> "NoteEvent":
    return cls(event_type="note_on", note=note, velocity=velocity, source=source)


@classmethod
def note_off(cls, note: int, source: str) -> "NoteEvent":
    return cls(event_type="note_off", note=note, velocity=0, source=source)
```

- [ ] **Step 3: Verify import shape locally**

Run:

```bash
python -c "from piano_led.core.models import NoteEvent, TimedMidiEvent, LoadedMidiSong, PlaybackState; print('ok')"
```

Expected:

```text
ok
```

- [ ] **Step 4: Commit the model additions**

```bash
git add src/piano_led/core/models.py
git commit -m "feat: add playback state models"
```

## Task 2: Add MIDI File Loader

**Files:**
- Create: `src/piano_led/songs/midi_loader.py`

- [ ] **Step 1: Create a focused MIDI loader module**

```python
"""Load MIDI files into absolute-timed note events for playback."""

from __future__ import annotations

import importlib
from pathlib import Path

from piano_led.core.models import LoadedMidiSong, NoteEvent, TimedMidiEvent


class MidiSongLoader:
    """Parse one MIDI file into a playback-ready song model."""

    def __init__(self, mido_module=None) -> None:
        self._mido = mido_module

    @property
    def mido(self):
        if self._mido is None:
            self._mido = importlib.import_module("mido")
        return self._mido

    def load(self, midi_path: Path, relative_path: str, display_title: str) -> LoadedMidiSong:
        midi_file = self.mido.MidiFile(str(midi_path))
        absolute_time = 0.0
        events: list[TimedMidiEvent] = []
        for message in midi_file:
            absolute_time += float(message.time)
            if not getattr(message, "is_meta", False):
                if message.type == "note_on" and message.velocity > 0:
                    events.append(
                        TimedMidiEvent(
                            time_seconds=absolute_time,
                            event=NoteEvent.note_on(message.note, message.velocity, "playback"),
                        )
                    )
                elif message.type in {"note_off", "note_on"} and getattr(message, "velocity", 0) == 0:
                    events.append(
                        TimedMidiEvent(
                            time_seconds=absolute_time,
                            event=NoteEvent.note_off(message.note, "playback"),
                        )
                    )
        return LoadedMidiSong(
            relative_path=relative_path,
            display_title=display_title,
            duration_seconds=absolute_time,
            events=events,
        )
```

- [ ] **Step 2: Make parse errors bubble as readable exceptions**

```python
try:
    midi_file = self.mido.MidiFile(str(midi_path))
except Exception as exc:
    raise RuntimeError(f"Unable to load MIDI file: {midi_path.name}") from exc
```

- [ ] **Step 3: Verify the module imports**

Run:

```bash
python -c "from piano_led.songs.midi_loader import MidiSongLoader; print(MidiSongLoader.__name__)"
```

Expected:

```text
MidiSongLoader
```

- [ ] **Step 4: Commit the MIDI loader**

```bash
git add src/piano_led/songs/midi_loader.py
git commit -m "feat: add midi playback loader"
```

## Task 3: Add the Playback Service

**Files:**
- Create: `src/piano_led/services/playback.py`

- [ ] **Step 1: Create the playback service skeleton**

```python
"""Background MIDI playback service for the first Practice page slice."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from piano_led.core.models import LoadedMidiSong, NoteEvent, PlaybackState
from piano_led.midi.output import MidiOutputPort
from piano_led.songs.midi_loader import MidiSongLoader


class PlaybackService:
    """Play one selected MIDI song at a time and expose serializable state."""

    def __init__(self, midi_output: MidiOutputPort | None = None, midi_loader: MidiSongLoader | None = None) -> None:
        self.midi_output = midi_output
        self.midi_loader = midi_loader or MidiSongLoader()
        self.state = PlaybackState()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._active_notes: set[int] = set()
```

- [ ] **Step 2: Add playback start and stop entrypoints**

```python
def play_song(self, midi_path: Path, relative_path: str, display_title: str, emit_note_event) -> dict:
    with self._lock:
        if self.state.status == "playing":
            return self.get_state()
        song = self.midi_loader.load(midi_path, relative_path, display_title)
        self._stop_event.clear()
        self.state = PlaybackState(
            status="playing",
            selected_song_path=relative_path,
            song_title=display_title,
            duration_seconds=song.duration_seconds,
            elapsed_seconds=0.0,
            active_notes=[],
            midi_output_enabled=self.midi_output is not None,
            error=None,
        )
        self._thread = threading.Thread(target=self._run_song, args=(song, emit_note_event), daemon=True)
        self._thread.start()
        return self.get_state()


def stop(self, emit_note_event, clear_leds) -> dict:
    self._stop_event.set()
    self._flush_active_notes(emit_note_event)
    clear_leds()
    with self._lock:
        self.state.status = "stopped"
        self.state.elapsed_seconds = 0.0
        self.state.active_notes = []
    return self.get_state()
```

- [ ] **Step 3: Add the background timing loop**

```python
def _run_song(self, song: LoadedMidiSong, emit_note_event) -> None:
    start_time = time.monotonic()
    try:
        for timed_event in song.events:
            if self._stop_event.is_set():
                break
            while not self._stop_event.is_set():
                elapsed = time.monotonic() - start_time
                if elapsed >= timed_event.time_seconds:
                    break
                time.sleep(0.002)
            if self._stop_event.is_set():
                break
            emit_note_event(timed_event.event)
            self._handle_active_note(timed_event.event)
            with self._lock:
                self.state.elapsed_seconds = min(timed_event.time_seconds, song.duration_seconds)
                self.state.active_notes = sorted(self._active_notes)
        self._finish_song(emit_note_event)
    except Exception as exc:
        with self._lock:
            self.state.status = "stopped"
            self.state.error = str(exc)
            self.state.active_notes = []
```

- [ ] **Step 4: Add note flushing and MIDI output helpers**

```python
def _handle_active_note(self, event: NoteEvent) -> None:
    if event.event_type == "note_on":
        self._active_notes.add(event.note)
    elif event.event_type == "note_off":
        self._active_notes.discard(event.note)
    if self.midi_output is not None:
        try:
            self.midi_output.send(event)
        except Exception:
            with self._lock:
                self.state.midi_output_enabled = False


def _flush_active_notes(self, emit_note_event) -> None:
    for note in sorted(self._active_notes):
        note_off = NoteEvent.note_off(note, "playback")
        emit_note_event(note_off)
        if self.midi_output is not None:
            try:
                self.midi_output.send(note_off)
            except Exception:
                pass
    self._active_notes.clear()


def _finish_song(self, emit_note_event) -> None:
    self._flush_active_notes(emit_note_event)
    with self._lock:
        self.state.status = "stopped"
        self.state.elapsed_seconds = self.state.duration_seconds
        self.state.active_notes = []
```

- [ ] **Step 5: Add a serializable getter**

```python
def get_state(self) -> dict:
    with self._lock:
        return self.state.to_dict()
```

- [ ] **Step 6: Verify the module imports**

Run:

```bash
python -c "from piano_led.services.playback import PlaybackService; print(PlaybackService.__name__)"
```

Expected:

```text
PlaybackService
```

- [ ] **Step 7: Commit the playback service**

```bash
git add src/piano_led/services/playback.py
git commit -m "feat: add playback service"
```

## Task 4: Wire Playback into the Runtime and App

**Files:**
- Modify: `src/piano_led/app.py`
- Modify: `src/piano_led/services/runtime.py`

- [ ] **Step 1: Pass MIDI output into the runtime from the application factory**

```python
runtime = PianoLedRuntime(
    settings=settings,
    keymap=keymap,
    led_driver=led_driver,
    settings_store=settings_store,
    keymap_store=keymap_store,
    state_store=state_store,
    song_library=song_library,
    midi_output=midi_output,
)
```

- [ ] **Step 2: Extend the runtime constructor to own playback**

```python
from piano_led.midi.output import MidiOutputPort
from piano_led.services.playback import PlaybackService


def __init__(
    self,
    settings: AppSettings,
    keymap: Keymap,
    led_driver: LedDriver,
    settings_store: SettingsStore | None = None,
    keymap_store: KeymapStore | None = None,
    state_store: StateStore | None = None,
    song_library: SongLibrary | None = None,
    midi_output: MidiOutputPort | None = None,
) -> None:
    self.settings = settings
    self.keymap = keymap
    self.led_driver = led_driver
    self.settings_store = settings_store
    self.keymap_store = keymap_store
    self.state_store = state_store or StateStore()
    self.song_library = song_library
    self.midi_output = midi_output
    self.playback = PlaybackService(midi_output=midi_output)
```

- [ ] **Step 3: Block live LED rendering while playback is active**

```python
def handle_note_event(self, event: NoteEvent) -> None:
    self.last_note_event = {
        "event_type": event.event_type,
        "note": event.note,
        "velocity": event.velocity,
        "source": event.source,
    }
    if event.source != "playback" and self.playback.get_state()["status"] == "playing":
        self.refresh_state()
        return
```

- [ ] **Step 4: Add playback start and stop runtime methods**

```python
def start_playback(self) -> dict:
    selected_song = self.get_selected_song()
    if selected_song is None:
        raise RuntimeError("No song selected. Choose a MIDI file on the Songs page first.")
    midi_path = self.song_library.root / selected_song["relative_path"]
    payload = self.playback.play_song(
        midi_path=midi_path,
        relative_path=selected_song["relative_path"],
        display_title=selected_song["display_title"],
        emit_note_event=self.handle_note_event,
    )
    self.refresh_state()
    return payload


def stop_playback(self) -> dict:
    payload = self.playback.stop(emit_note_event=self.handle_note_event, clear_leds=self.clear_leds)
    self.refresh_state()
    return payload


def get_playback_state(self) -> dict:
    self.refresh_state()
    return self.playback.get_state()
```

- [ ] **Step 5: Publish playback state through the state store**

```python
self.state_store.update(
    settings=self.settings.to_dict(),
    active_notes=sorted(self.active_notes),
    last_note_event=self.last_note_event,
    calibration=calibration,
    keymap=self.keymap.to_dict(),
    songs=self.song_snapshot["songs"],
    selected_song_path=self.song_snapshot["selected_song_path"],
    selected_song=self.song_snapshot["selected_song"],
    playback=self.playback.get_state(),
)
```

- [ ] **Step 6: Verify the CLI still boots**

Run:

```bash
python -m piano_led status
```

Expected:

```text
The command prints one line that starts with:
Piano LED runtime ready:
```

- [ ] **Step 7: Commit runtime wiring**

```bash
git add src/piano_led/app.py src/piano_led/services/runtime.py
git commit -m "feat: wire playback into runtime"
```

## Task 5: Add Practice Playback API and UI

**Files:**
- Modify: `src/piano_led/web/server.py`

- [ ] **Step 1: Add playback API routes**

```python
if method == "GET" and path == "/api/playback":
    return _json_response(start_response, runtime.get_playback_state())

if method == "POST" and path == "/api/playback/play":
    try:
        return _json_response(start_response, runtime.start_playback())
    except RuntimeError as error:
        return _json_response(start_response, {"error": str(error)}, status="400 Bad Request")

if method == "POST" and path == "/api/playback/stop":
    return _json_response(start_response, runtime.stop_playback())
```

- [ ] **Step 2: Extend the Practice page markup with playback controls**

```html
<section class="panel">
  <h2>Playback</h2>
  <button onclick="playSelectedSong()">Play Selected Song</button>
  <button onclick="stopPlayback()">Stop</button>
  <pre id="playback-output">Waiting for playback state...</pre>
</section>
```

- [ ] **Step 3: Add Practice page JavaScript for playback state**

```javascript
async function refreshPractice() {
  const selectionPayload = await fetchJson('/api/song-selection');
  const playbackPayload = await fetchJson('/api/playback');
  const emptyState = document.getElementById('practice-empty-state');
  const output = document.getElementById('selected-song-output');
  if (!selectionPayload.songs.length) {
    emptyState.hidden = false;
    emptyState.textContent = 'No MIDI files found in data/songs/midi yet.';
    output.hidden = true;
    output.textContent = '';
  } else if (!selectionPayload.selected_song) {
    emptyState.hidden = false;
    emptyState.textContent = 'No song selected yet. Choose a MIDI file on the Songs page to begin practicing.';
    output.hidden = true;
    output.textContent = '';
  } else {
    emptyState.hidden = true;
    output.hidden = false;
    output.textContent = JSON.stringify(selectionPayload, null, 2);
  }
  document.getElementById('playback-output').textContent = JSON.stringify(playbackPayload, null, 2);
}

async function playSelectedSong() {
  const payload = await fetchJson('/api/playback/play', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: '{}'
  });
  document.getElementById('playback-output').textContent = JSON.stringify(payload, null, 2);
  await refreshPractice();
}

async function stopPlayback() {
  const payload = await fetchJson('/api/playback/stop', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: '{}'
  });
  document.getElementById('playback-output').textContent = JSON.stringify(payload, null, 2);
  await refreshPractice();
}
```

- [ ] **Step 4: Poll playback state while the page is open**

```javascript
refreshPractice();
setInterval(refreshPractice, 500);
```

- [ ] **Step 5: Verify the server imports**

Run:

```bash
python -c "from piano_led.web.server import create_web_app; print(callable(create_web_app))"
```

Expected:

```text
True
```

- [ ] **Step 6: Commit the web playback slice**

```bash
git add src/piano_led/web/server.py
git commit -m "feat: add practice playback controls"
```

## Task 6: Update Stage Docs and Run Pi Smoke Test

**Files:**
- Modify: `docs/stages/stage-05-midi-playback.md`

- [ ] **Step 1: Update the stage document with the implemented first slice**

```markdown
## Playback first slice implemented
- shared song selection feeds `/practice`
- `/practice` can play the selected MIDI from the beginning
- playback sends note events to LEDs
- playback sends note events to MIDI output when configured
- stop and end-of-song both clear LEDs and send note-offs
```

- [ ] **Step 2: Add Pi smoke-test instructions to the stage doc**

```markdown
## Pi smoke test
1. `git pull`
2. `python3 -m piano_led status`
3. `sudo python3 -m piano_led web-serve --host 0.0.0.0 --port 8080 --with-live`
4. Open `/songs`, select a MIDI file, then open `/practice`.
5. Press Play and confirm the piano sounds and LEDs follow the notes.
6. Press Stop and confirm the strip clears immediately.
7. Let the song finish and confirm the strip clears with no hung notes.
```

- [ ] **Step 3: Do a local sanity pass before handing off to the Pi**

Run:

```bash
python -m piano_led status
python -c "from piano_led.web.server import create_web_app; print('web ok')"
```

Expected:

```text
The first command prints one line that starts with `Piano LED runtime ready:`
web ok
```

- [ ] **Step 4: Commit the doc update**

```bash
git add docs/stages/stage-05-midi-playback.md
git commit -m "docs: update stage 5 playback status"
```

## Verification Notes

By explicit user preference, skip automated unit tests for this slice. Verification should happen by having the user pull the branch on the Pi and report:

- whether playback starts
- whether the piano sounds through MIDI output
- whether LEDs track the song
- whether Stop clears the strip
- whether end-of-song clears the strip
- any errors shown on `/practice`
