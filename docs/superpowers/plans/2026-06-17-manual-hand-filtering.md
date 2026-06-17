# Manual Hand Filtering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-song manual hand setup so Practice playback can run in `both`, `left`, or `right` mode with hand-specific LED colors.

**Architecture:** Extend parsed MIDI playback events with track and channel metadata, store per-song hand assignments in JSON sidecar files, and filter playback events before the timing thread starts. The Songs page owns hand setup, the Practice page owns hand-mode selection, and the runtime publishes the selected mode and filtered playback state. By user preference, verification is done with local sanity checks plus manual Pi smoke testing instead of automated unit tests.

**Tech Stack:** Python 3.11, `mido`, existing WSGI web UI, JSON metadata files, existing runtime/playback services, Raspberry Pi smoke tests

---

## File Structure

- `src/piano_led/core/models.py`
  Add playback event metadata needed for hand classification and add `hand_mode` to playback state.

- `src/piano_led/config/settings.py`
  Extend LED settings with left-hand and right-hand colors, including black-key variants.

- `src/piano_led/songs/midi_loader.py`
  Parse track and channel metadata into playback-ready events and expose a simple summary of available tracks and channels for the UI.

- `src/piano_led/songs/hand_config.py`
  New focused storage module for per-song hand metadata under `data/songs/metadata/`.

- `src/piano_led/services/playback.py`
  Add hand-mode-aware filtering before playback starts and preserve hand tags through rendering.

- `src/piano_led/services/runtime.py`
  Own selected hand mode, expose song hand config helpers, and route hand-aware playback and color selection.

- `src/piano_led/app.py`
  Wire the new song-hand-config store into the runtime.

- `src/piano_led/web/server.py`
  Add API routes and UI for per-song hand setup on Songs and hand mode selection on Practice.

- `docs/stages/stage-05-midi-playback.md`
  Update Stage 5 status and Pi smoke-test instructions for manual hand filtering.

## Task 1: Extend Shared Models and Settings

**Files:**
- Modify: `src/piano_led/core/models.py`
- Modify: `src/piano_led/config/settings.py`

- [ ] **Step 1: Extend playback event and playback state models**

```python
@dataclass(frozen=True)
class TimedMidiEvent:
    """One note event scheduled at an absolute playback time in seconds."""

    time_seconds: float
    event: NoteEvent
    track_index: int | None = None
    channel: int | None = None
    hand: str = "unassigned"


@dataclass
class PlaybackState:
    """Serializable runtime state for playback and hand-filtering views."""

    status: str = "stopped"
    selected_song_path: str | None = None
    song_title: str | None = None
    duration_seconds: float = 0.0
    elapsed_seconds: float = 0.0
    active_notes: list[int] = field(default_factory=list)
    midi_output_enabled: bool = False
    hand_mode: str = "both"
    error: str | None = None
```

- [ ] **Step 2: Add hand-specific LED colors to settings**

```python
@dataclass
class LedSettings:
    """LED-strip parameters, backend selection, and hand-aware colors."""

    total_leds: int = 176
    leds_per_meter: int = 144
    note_color: str = "#00b894"
    black_key_color: str = "#0984e3"
    use_black_key_color: bool = True
    left_hand_note_color: str = "#00b894"
    left_hand_black_key_color: str = "#0984e3"
    right_hand_note_color: str = "#e17055"
    right_hand_black_key_color: str = "#d63031"
    strip_direction: str = "left_to_right"
    default_first_led: int = 0
    backend: str = "fake"
    gpio_pin: int = 18
    brightness: int = 128
    dma_channel: int = 10
    pwm_frequency_hz: int = 800000
    invert_signal: bool = False
    channel: int = 0
```

- [ ] **Step 3: Verify the new types import cleanly**

Run:

```bash
& 'C:\Users\flipf\AppData\Local\Programs\Python\Python312\python.exe' -c "from piano_led.core.models import TimedMidiEvent, PlaybackState; from piano_led.config.settings import LedSettings; print('ok')"
```

Expected:

```text
ok
```

- [ ] **Step 4: Commit shared model and settings updates**

```bash
git add src/piano_led/core/models.py src/piano_led/config/settings.py
git commit -m "feat: add hand-aware playback models"
```

## Task 2: Add Per-Song Hand Metadata Storage

**Files:**
- Create: `src/piano_led/songs/hand_config.py`

- [ ] **Step 1: Create hand metadata dataclass and store**

```python
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
        return asdict(self)


class SongHandConfigStore:
    """Load and save hand setup JSON files for each MIDI song."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path_for_song(self, relative_path: str) -> Path:
        safe_name = Path(relative_path).with_suffix(".json").name
        return self.root / safe_name

    def load(self, relative_path: str) -> SongHandConfig:
        path = self._path_for_song(relative_path)
        if not path.exists():
            return SongHandConfig(relative_path=relative_path)
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return SongHandConfig(
            relative_path=payload.get("relative_path", relative_path),
            left_hand_tracks=payload.get("left_hand_tracks", []),
            right_hand_tracks=payload.get("right_hand_tracks", []),
            left_hand_channels=payload.get("left_hand_channels", []),
            right_hand_channels=payload.get("right_hand_channels", []),
        )

    def save(self, config: SongHandConfig) -> SongHandConfig:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path_for_song(config.relative_path)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(config.to_dict(), handle, indent=2)
        return config
```

- [ ] **Step 2: Verify the new store imports**

Run:

```bash
& 'C:\Users\flipf\AppData\Local\Programs\Python\Python312\python.exe' -c "from piano_led.songs.hand_config import SongHandConfig, SongHandConfigStore; print(SongHandConfig.__name__, SongHandConfigStore.__name__)"
```

Expected:

```text
SongHandConfig SongHandConfigStore
```

- [ ] **Step 3: Commit the hand metadata store**

```bash
git add src/piano_led/songs/hand_config.py
git commit -m "feat: add per-song hand config storage"
```

## Task 3: Extend MIDI Loader with Track and Channel Summaries

**Files:**
- Modify: `src/piano_led/songs/midi_loader.py`

- [ ] **Step 1: Add lightweight summary dataclasses for the Songs page**

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class MidiSongSummary:
    """Available track and channel info for manual hand assignment."""

    relative_path: str
    display_title: str
    track_indices: list[int] = field(default_factory=list)
    channels: list[int] = field(default_factory=list)
```

- [ ] **Step 2: Parse events with track and channel metadata**

```python
def load(self, midi_path: Path, relative_path: str, display_title: str) -> LoadedMidiSong:
    try:
        midi_file = self.mido.MidiFile(str(midi_path))
    except Exception as exc:
        raise RuntimeError(f"Unable to load MIDI file: {midi_path.name}") from exc

    events: list[TimedMidiEvent] = []
    duration_seconds = 0.0
    for track_index, track in enumerate(midi_file.tracks):
        absolute_ticks = 0
        tempo = 500000
        absolute_seconds = 0.0
        for message in track:
            absolute_ticks += int(message.time)
            absolute_seconds += self.mido.tick2second(int(message.time), midi_file.ticks_per_beat, tempo)
            if getattr(message, "is_meta", False):
                if message.type == "set_tempo":
                    tempo = message.tempo
                continue
            duration_seconds = max(duration_seconds, absolute_seconds)
            if message.type == "note_on" and message.velocity > 0:
                events.append(
                    TimedMidiEvent(
                        time_seconds=absolute_seconds,
                        event=NoteEvent.note_on(message.note, message.velocity, "playback"),
                        track_index=track_index,
                        channel=getattr(message, "channel", None),
                    )
                )
            elif message.type == "note_off" or (message.type == "note_on" and message.velocity == 0):
                events.append(
                    TimedMidiEvent(
                        time_seconds=absolute_seconds,
                        event=NoteEvent.note_off(message.note, "playback"),
                        track_index=track_index,
                        channel=getattr(message, "channel", None),
                    )
                )
    events.sort(key=lambda item: (item.time_seconds, 0 if item.event.event_type == "note_off" else 1))
    return LoadedMidiSong(
        relative_path=relative_path,
        display_title=display_title,
        duration_seconds=duration_seconds,
        events=events,
    )
```

- [ ] **Step 3: Add a summary helper for track and channel choices**

```python
def summarize(self, midi_path: Path, relative_path: str, display_title: str) -> MidiSongSummary:
    try:
        midi_file = self.mido.MidiFile(str(midi_path))
    except Exception as exc:
        raise RuntimeError(f"Unable to inspect MIDI file: {midi_path.name}") from exc

    track_indices: list[int] = []
    channels: set[int] = set()
    for track_index, track in enumerate(midi_file.tracks):
        saw_note_message = False
        for message in track:
            if getattr(message, "is_meta", False):
                continue
            if message.type in {"note_on", "note_off"}:
                saw_note_message = True
                if hasattr(message, "channel"):
                    channels.add(int(message.channel))
        if saw_note_message:
            track_indices.append(track_index)
    return MidiSongSummary(
        relative_path=relative_path,
        display_title=display_title,
        track_indices=track_indices,
        channels=sorted(channels),
    )
```

- [ ] **Step 4: Verify the loader still imports**

Run:

```bash
& 'C:\Users\flipf\AppData\Local\Programs\Python\Python312\python.exe' -c "from piano_led.songs.midi_loader import MidiSongLoader, MidiSongSummary; print(MidiSongLoader.__name__, MidiSongSummary.__name__)"
```

Expected:

```text
MidiSongLoader MidiSongSummary
```

- [ ] **Step 5: Commit the loader extensions**

```bash
git add src/piano_led/songs/midi_loader.py
git commit -m "feat: add midi hand assignment metadata"
```

## Task 4: Add Hand Filtering to Playback and Runtime

**Files:**
- Modify: `src/piano_led/services/playback.py`
- Modify: `src/piano_led/services/runtime.py`

- [ ] **Step 1: Add hand classification and filtering helpers to playback**

```python
def _event_matches_hand(self, timed_event: TimedMidiEvent, hand_config, hand_name: str) -> bool:
    track_values = getattr(hand_config, f"{hand_name}_hand_tracks")
    channel_values = getattr(hand_config, f"{hand_name}_hand_channels")
    return (
        timed_event.track_index in track_values
        or timed_event.channel in channel_values
    )


def _apply_hand_tags(self, events: list[TimedMidiEvent], hand_config) -> list[TimedMidiEvent]:
    tagged: list[TimedMidiEvent] = []
    for event in events:
        hand = "unassigned"
        if self._event_matches_hand(event, hand_config, "left"):
            hand = "left"
        elif self._event_matches_hand(event, hand_config, "right"):
            hand = "right"
        tagged.append(
            TimedMidiEvent(
                time_seconds=event.time_seconds,
                event=event.event,
                track_index=event.track_index,
                channel=event.channel,
                hand=hand,
            )
        )
    return tagged


def _filter_events_for_mode(self, events: list[TimedMidiEvent], hand_mode: str) -> list[TimedMidiEvent]:
    if hand_mode == "both":
        return events
    return [event for event in events if event.hand == hand_mode]
```

- [ ] **Step 2: Extend `play_song` to accept hand mode and hand config**

```python
def play_song(
    self,
    midi_path: Path,
    relative_path: str,
    display_title: str,
    emit_note_event: Callable[[NoteEvent], None],
    clear_leds: Callable[[], None],
    hand_mode: str,
    hand_config,
) -> dict:
    song = self.midi_loader.load(midi_path, relative_path, display_title)
    tagged_events = self._apply_hand_tags(song.events, hand_config)
    filtered_events = self._filter_events_for_mode(tagged_events, hand_mode)
    self.state = PlaybackState(
        status="playing",
        selected_song_path=relative_path,
        song_title=display_title,
        duration_seconds=song.duration_seconds,
        elapsed_seconds=0.0,
        active_notes=[],
        midi_output_enabled=midi_output_enabled,
        hand_mode=hand_mode,
        error=None,
    )
    self._thread = threading.Thread(
        target=self._run_song,
        args=(
            LoadedMidiSong(
                relative_path=song.relative_path,
                display_title=song.display_title,
                duration_seconds=song.duration_seconds,
                events=filtered_events,
            ),
        ),
        daemon=True,
    )
    self._thread.start()
    return self.state.to_dict()
```

- [ ] **Step 3: Validate missing left/right mappings in runtime**

```python
def set_playback_hand_mode(self, hand_mode: str) -> dict:
    if hand_mode not in {"both", "left", "right"}:
        raise ValueError(f"Unsupported hand mode: {hand_mode}")
    self.playback_hand_mode = hand_mode
    self.refresh_state()
    return self.get_playback_state()


def start_playback(self) -> dict:
    selected_song = self.get_selected_song()
    if selected_song is None:
        raise RuntimeError("No song selected. Choose a MIDI file on the Songs page first.")
    if self.song_library is None or self.song_hand_config_store is None:
        raise RuntimeError("Song playback dependencies are not configured.")
    hand_config = self.song_hand_config_store.load(selected_song["relative_path"])
    if self.playback_hand_mode == "left" and not (hand_config.left_hand_tracks or hand_config.left_hand_channels):
        raise RuntimeError("No left-hand mapping saved for this song yet.")
    if self.playback_hand_mode == "right" and not (hand_config.right_hand_tracks or hand_config.right_hand_channels):
        raise RuntimeError("No right-hand mapping saved for this song yet.")
    payload = self.playback.play_song(
        midi_path=self.song_library.midi_root / selected_song["relative_path"],
        relative_path=selected_song["relative_path"],
        display_title=selected_song["display_title"],
        emit_note_event=self.handle_note_event,
        clear_leds=self.clear_leds,
        hand_mode=self.playback_hand_mode,
        hand_config=hand_config,
    )
    self.refresh_state()
    return payload
```

- [ ] **Step 4: Add hand-aware LED color selection in runtime**

```python
def note_color_for(self, note: int, hand: str = "unassigned") -> tuple[int, int, int]:
    if hand == "left":
        if is_black_key(note):
            return hex_to_rgb(self.settings.led.left_hand_black_key_color)
        return hex_to_rgb(self.settings.led.left_hand_note_color)
    if hand == "right":
        if is_black_key(note):
            return hex_to_rgb(self.settings.led.right_hand_black_key_color)
        return hex_to_rgb(self.settings.led.right_hand_note_color)
    if self.settings.led.use_black_key_color and is_black_key(note):
        return hex_to_rgb(self.settings.led.black_key_color)
    return hex_to_rgb(self.settings.led.note_color)
```

- [ ] **Step 5: Preserve hand tag through emitted playback note events**

```python
def handle_note_event(self, event: NoteEvent, hand: str = "unassigned") -> None:
    self.last_note_event = {
        "event_type": event.event_type,
        "note": event.note,
        "velocity": event.velocity,
        "source": event.source,
        "hand": hand,
    }
```

Then update playback emission to pass the hand alongside the event:

```python
def _emit_event(self, timed_event: TimedMidiEvent) -> None:
    if timed_event.event.event_type == "note_on":
        self._active_notes.add(timed_event.event.note)
    elif timed_event.event.event_type == "note_off":
        self._active_notes.discard(timed_event.event.note)

    if self._emit_note_event is not None:
        self._emit_note_event(timed_event.event, timed_event.hand)

    if self.midi_output is not None and self.state.midi_output_enabled:
        try:
            self.midi_output.send(timed_event.event)
        except Exception:
            with self._lock:
                self.state.midi_output_enabled = False
```

- [ ] **Step 6: Verify runtime boot and state shape**

Run:

```bash
& 'C:\Users\flipf\AppData\Local\Programs\Python\Python312\python.exe' -m piano_led status
& 'C:\Users\flipf\AppData\Local\Programs\Python\Python312\python.exe' -c "from pathlib import Path; from piano_led.app import build_application; app = build_application(Path('.'), initialize_leds=False); print(app.runtime.get_playback_state())"
```

Expected:

```text
The first command prints one line that starts with `Piano LED runtime ready:`
The second command prints a playback state dictionary containing `"hand_mode": "both"`
```

- [ ] **Step 7: Commit playback and runtime hand filtering**

```bash
git add src/piano_led/services/playback.py src/piano_led/services/runtime.py
git commit -m "feat: add manual playback hand filtering"
```

## Task 5: Wire the Hand Config Store into the App

**Files:**
- Modify: `src/piano_led/app.py`

- [ ] **Step 1: Create and pass the hand config store**

```python
from piano_led.songs.hand_config import SongHandConfigStore

song_hand_config_root = root / "data" / "songs" / "metadata"
song_hand_config_store = SongHandConfigStore(song_hand_config_root)

runtime = PianoLedRuntime(
    settings=settings,
    keymap=keymap,
    led_driver=led_driver,
    settings_store=settings_store,
    keymap_store=keymap_store,
    state_store=state_store,
    song_library=song_library,
    midi_output=midi_output,
    song_hand_config_store=song_hand_config_store,
)
```

- [ ] **Step 2: Verify the app still builds**

Run:

```bash
& 'C:\Users\flipf\AppData\Local\Programs\Python\Python312\python.exe' -c "from pathlib import Path; from piano_led.app import build_application; app = build_application(Path('.'), initialize_leds=False); print(type(app.runtime).__name__)"
```

Expected:

```text
PianoLedRuntime
```

- [ ] **Step 3: Commit app wiring**

```bash
git add src/piano_led/app.py
git commit -m "feat: wire song hand config store"
```

## Task 6: Add Songs Page Hand Setup APIs and UI

**Files:**
- Modify: `src/piano_led/web/server.py`

- [ ] **Step 1: Add song hand config routes**

```python
if method == "GET" and path == "/api/song-hand-config":
    relative_path = environ.get("QUERY_STRING", "").removeprefix("relative_path=")
    try:
        payload = runtime.get_song_hand_config_state(relative_path)
    except RuntimeError as error:
        return _json_response(start_response, {"error": str(error)}, status="400 Bad Request")
    return _json_response(start_response, payload)

if method == "POST" and path == "/api/song-hand-config":
    try:
        payload = runtime.save_song_hand_config(
            relative_path=str(body["relative_path"]),
            left_hand_tracks=[int(value) for value in body.get("left_hand_tracks", [])],
            right_hand_tracks=[int(value) for value in body.get("right_hand_tracks", [])],
            left_hand_channels=[int(value) for value in body.get("left_hand_channels", [])],
            right_hand_channels=[int(value) for value in body.get("right_hand_channels", [])],
        )
    except (RuntimeError, ValueError, KeyError) as error:
        return _json_response(start_response, {"error": str(error)}, status="400 Bad Request")
    return _json_response(start_response, payload)
```

- [ ] **Step 2: Add Songs page hand setup panel**

```html
<section class="panel">
  <h2>Hand Setup</h2>
  <p id="hand-setup-empty">Select a song to configure left and right hand sources.</p>
  <div id="hand-setup-editor" hidden>
    <label>Left Hand Tracks</label>
    <div id="left-track-options"></div>
    <label>Right Hand Tracks</label>
    <div id="right-track-options"></div>
    <label>Left Hand Channels</label>
    <div id="left-channel-options"></div>
    <label>Right Hand Channels</label>
    <div id="right-channel-options"></div>
    <button id="save-hand-setup-button" onclick="saveHandSetup()">Save Hand Setup</button>
  </div>
  <pre id="hand-setup-output">No hand setup loaded yet.</pre>
</section>
```

- [ ] **Step 3: Add Songs page JavaScript to load track/channel choices**

```javascript
async function refreshHandSetup(selectedPath) {
  const emptyState = document.getElementById('hand-setup-empty');
  const editor = document.getElementById('hand-setup-editor');
  const output = document.getElementById('hand-setup-output');
  if (!selectedPath) {
    emptyState.hidden = false;
    editor.hidden = true;
    output.textContent = 'Select a song to configure left and right hand sources.';
    return;
  }
  const payload = await fetchJson('/api/song-hand-config?relative_path=' + encodeURIComponent(selectedPath));
  emptyState.hidden = true;
  editor.hidden = false;
  renderCheckboxGroup('left-track-options', payload.summary.track_indices, payload.config.left_hand_tracks, 'left_track');
  renderCheckboxGroup('right-track-options', payload.summary.track_indices, payload.config.right_hand_tracks, 'right_track');
  renderCheckboxGroup('left-channel-options', payload.summary.channels, payload.config.left_hand_channels, 'left_channel');
  renderCheckboxGroup('right-channel-options', payload.summary.channels, payload.config.right_hand_channels, 'right_channel');
  output.textContent = JSON.stringify(payload, null, 2);
}
```

- [ ] **Step 4: Add Songs page save handler**

```javascript
async function saveHandSetup() {
  const relativePath = document.getElementById('song-select').value;
  const payload = await fetchJson('/api/song-hand-config', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      relative_path: relativePath,
      left_hand_tracks: collectCheckedValues('left_track'),
      right_hand_tracks: collectCheckedValues('right_track'),
      left_hand_channels: collectCheckedValues('left_channel'),
      right_hand_channels: collectCheckedValues('right_channel')
    })
  });
  document.getElementById('hand-setup-output').textContent = JSON.stringify(payload, null, 2);
  await refreshHandSetup(relativePath);
}
```

- [ ] **Step 5: Hook hand setup refresh into song selection**

```javascript
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
    await refreshHandSetup('');
    return;
  }
  emptyState.hidden = true;
  select.hidden = false;
  select.disabled = false;
  button.hidden = false;
  if (!songsPayload.songs.some(song => song.relative_path === effectiveSelectedPath)) {
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = 'Choose a song';
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
  } else {
    output.textContent = JSON.stringify(selectionPayload, null, 2);
  }
  await refreshHandSetup(selectionPayload.selected_song_path || effectiveSelectedPath || '');
}

document.getElementById('song-select').addEventListener('change', async () => {
  updateSongSelectionButton();
  await refreshHandSetup(document.getElementById('song-select').value);
});
```

- [ ] **Step 6: Verify the server still imports**

Run:

```bash
& 'C:\Users\flipf\AppData\Local\Programs\Python\Python312\python.exe' -c "from piano_led.web.server import create_web_app; print(callable(create_web_app))"
```

Expected:

```text
True
```

- [ ] **Step 7: Commit Songs page hand setup**

```bash
git add src/piano_led/web/server.py
git commit -m "feat: add songs hand setup editor"
```

## Task 7: Add Practice Hand Mode Selector

**Files:**
- Modify: `src/piano_led/web/server.py`

- [ ] **Step 1: Add playback hand mode routes**

```python
if method == "POST" and path == "/api/playback-mode":
    try:
        payload = runtime.set_playback_hand_mode(str(body["hand_mode"]))
    except (RuntimeError, ValueError, KeyError) as error:
        return _json_response(start_response, {"error": str(error)}, status="400 Bad Request")
    return _json_response(start_response, payload)
```

- [ ] **Step 2: Add Practice hand mode selector markup**

```html
<label>Playback Hand Mode</label>
<select id="playback-hand-mode">
  <option value="both">Both</option>
  <option value="left">Left</option>
  <option value="right">Right</option>
</select>
```

- [ ] **Step 3: Refresh Practice page from playback state**

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
  document.getElementById('playback-hand-mode').value = playbackPayload.hand_mode || 'both';
  document.getElementById('playback-output').textContent = JSON.stringify(playbackPayload, null, 2);
}
```

- [ ] **Step 4: Add hand mode change handler**

```javascript
document.getElementById('playback-hand-mode').addEventListener('change', async (event) => {
  const payload = await fetchJson('/api/playback-mode', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({hand_mode: event.target.value})
  });
  document.getElementById('playback-output').textContent = JSON.stringify(payload, null, 2);
  await refreshPractice();
});
```

- [ ] **Step 5: Verify status and import sanity again**

Run:

```bash
& 'C:\Users\flipf\AppData\Local\Programs\Python\Python312\python.exe' -m piano_led status
& 'C:\Users\flipf\AppData\Local\Programs\Python\Python312\python.exe' -c "from piano_led.web.server import create_web_app; print('web ok')"
```

Expected:

```text
The first command prints one line that starts with `Piano LED runtime ready:`
web ok
```

- [ ] **Step 6: Commit Practice hand mode UI**

```bash
git add src/piano_led/web/server.py
git commit -m "feat: add practice hand mode selector"
```

## Task 8: Update Stage Docs and Pi Smoke Steps

**Files:**
- Modify: `docs/stages/stage-05-midi-playback.md`

- [ ] **Step 1: Update Stage 5 status**

```markdown
## Manual hand filtering implemented
- Songs page can save left/right hand assignment by track and channel
- Practice page can switch between `both`, `left`, and `right`
- playback uses hand-specific LED colors
- black keys use hand-specific black-key colors
- missing hand mappings fail with a friendly error
```

- [ ] **Step 2: Add Pi smoke-test instructions**

```markdown
## Pi smoke test for hand filtering
1. `git pull`
2. `sudo python3 -m piano_led web-serve --host 0.0.0.0 --port 8080 --with-live`
3. Open `/songs` and select a song with separated hands.
4. Save left and right hand track or channel assignments.
5. Open `/practice` and test `Both`, `Left`, and `Right`.
6. Confirm left and right notes keep their own hand colors in `Both`.
7. Confirm black keys use the black-key color for their hand.
8. Try `Left` or `Right` without a saved mapping on another song and confirm the app shows a friendly error.
```

- [ ] **Step 3: Do the final local sanity pass**

Run:

```bash
& 'C:\Users\flipf\AppData\Local\Programs\Python\Python312\python.exe' -m piano_led status
& 'C:\Users\flipf\AppData\Local\Programs\Python\Python312\python.exe' -c "from pathlib import Path; from piano_led.app import build_application; app = build_application(Path('.'), initialize_leds=False); print(app.runtime.get_playback_state())"
```

Expected:

```text
The first command prints one line that starts with `Piano LED runtime ready:`
The second command prints a playback state dictionary containing the current hand mode
```

- [ ] **Step 4: Commit the stage doc update**

```bash
git add docs/stages/stage-05-midi-playback.md
git commit -m "docs: update stage 5 hand filtering status"
```

## Verification Notes

By explicit user preference, skip automated unit tests for this slice. Verification should happen by having the user pull the repo on the Pi and report:

- whether hand setup saves per song
- whether `left`, `right`, and `both` playback modes work
- whether each hand keeps its own LED color in `both`
- whether black keys use the correct hand-specific black-key color
- whether songs without hand setup fail safely with a friendly message
