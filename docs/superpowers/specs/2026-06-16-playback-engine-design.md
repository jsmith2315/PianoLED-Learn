# Playback Engine First Slice Design

## Goal

Implement the first usable MIDI playback slice for Piano LED Learn. The user should be able to choose a MIDI file on the existing Songs page, open the Practice page, press Play, hear the song on the piano through MIDI output, and see the mapped LEDs follow the song. Pressing Stop, or reaching the end of the song, must clear the strip and send note-off events for any playback notes that are still active.

This design intentionally keeps the first slice narrow:

- playback controls live on `/practice` only
- controls are `Play` and `Stop` only
- playback always starts from the beginning
- playback owns LED output while active
- live piano input stays available to the app, but does not change LEDs during playback

The design also preserves room for later expansion into pause, looping, hand filtering, assisted practice, and mixed live-plus-playback rendering.

## Scope

Included in this slice:

- load the currently selected MIDI file from the shared song selection state
- parse the MIDI file into timed note events
- play timed note events from start to finish
- light LEDs in sync with playback
- send playback note-on and note-off events to MIDI output when configured
- expose playback state to the web UI
- allow the Practice page to start and stop playback

Not included in this slice:

- pause or resume
- seek or scrub
- loop ranges
- hand filtering
- waiting for correct notes
- falling notes or score display
- persistent playback history

## Recommended Architecture

The playback engine should be implemented as a runtime-owned service. The existing runtime already owns settings, selected song state, LED output coordination, and web-visible state, so the best fit is to keep the runtime as the top-level coordinator and add a focused playback subsystem under it.

Three approaches were considered:

1. Runtime-owned playback service
2. Put all playback logic directly into `PianoLedRuntime`
3. Build a more isolated transport subsystem from day one

The recommended approach is the runtime-owned playback service because it creates a clean enough boundary now without overbuilding. It keeps the first slice understandable and testable while making later transport upgrades easier.

## Component Design

### `src/piano_led/songs/midi_loader.py`

This module should load a selected MIDI file and convert it into a simple in-memory playback model. It should:

- read the MIDI file with a Python 3.11 compatible library already planned for this project
- convert delta times into absolute times in seconds
- extract note-on and note-off events
- return events sorted by playback time
- calculate song duration for the UI

The loader should stay focused on file parsing and time conversion only. It should not know about LEDs, the web UI, or runtime state.

### `src/piano_led/core/models.py`

This module should gain a few shared playback dataclasses so multiple layers use the same shapes. Likely additions:

- `TimedMidiEvent`
- `LoadedMidiSong`
- `PlaybackState`

These models should remain lightweight and serializable for easy use in runtime state and tests.

### `src/piano_led/services/playback.py`

This module should hold `PlaybackService`, the main engine for the first playback slice. It should:

- load the selected MIDI file through the song library and MIDI loader
- start playback in a background worker thread
- schedule events against `time.monotonic()`
- emit note events to LED and MIDI sinks
- track active playback notes
- expose `play_selected_song()`, `stop()`, and `get_state()`

The service should own playback timing details, but not overall app configuration or route handling.

### `src/piano_led/services/runtime.py`

The runtime should own one `PlaybackService` instance and act as the boundary between playback and the rest of the application. It should:

- start playback for the selected song
- stop playback on request
- expose playback state through the existing state store
- ignore live LED note rendering while playback is active
- still record live note events for future learning features

This keeps live MIDI input and playback coordinated in one place without making the runtime do all playback timing itself.

### `src/piano_led/web/server.py`

The web server should add:

- `POST /api/playback/play`
- `POST /api/playback/stop`
- `GET /api/playback`

The Practice page should gain:

- a `Play Selected Song` button
- a `Stop` button
- a status panel showing song title, state, elapsed time, duration, and any current playback error

The Songs page remains responsible only for selecting the current shared MIDI file.

## Data Flow

The first-slice playback flow should work like this:

1. The user selects a MIDI file on `/songs`.
2. The user opens `/practice` and presses `Play Selected Song`.
3. The web API calls `runtime.start_playback()`.
4. The runtime asks `PlaybackService` to load the selected song and start a worker thread.
5. The worker thread schedules note events using `time.monotonic()`.
6. Each playback note-on lights the mapped LED and sends MIDI note-on to the configured output port.
7. Each playback note-off clears that mapped LED and sends MIDI note-off to the configured output port.
8. When the song ends, or the user presses Stop, the service sends note-off events for any still-active playback notes, clears the strip, and marks playback stopped.

Playback-active notes and live-played notes should be tracked separately internally. For this slice, only playback-active notes affect the strip during playback, but the split prepares the code for later blended learning behavior.

## Behavioral Rules

### Play

- If no song is selected, Play returns a friendly error and playback does not start.
- If playback is already active, Play returns the current state and does not start a second playback worker.
- Playback always starts from the beginning of the selected song.

### Stop

- Stop must always send note-off events for any playback notes still active.
- Stop must always clear the LED strip.
- Stop should be safe to call even when playback is already stopped.

### End of Song

- End-of-song behavior must match manual Stop behavior.
- After the last event, the service sends any remaining note-offs, clears the strip, and returns to the stopped state.

### Live Piano Input During Playback

- Live piano key presses should still be visible to the app as note events.
- While playback is active, live note events should not change LED output.
- This is a temporary rule for the first slice and should be implemented in a way that can be relaxed later.

### MIDI Output Availability

- If MIDI output is configured and available, playback should send note events to the piano.
- If MIDI output is unavailable or not configured, playback should still run LED playback successfully.
- The playback state should expose whether MIDI output is active so the Practice page can explain what is happening.

### Parse or File Errors

- If the selected MIDI file cannot be loaded or parsed, playback stays stopped.
- The UI should receive a readable error message through playback state.
- A broken MIDI file should not crash the runtime or web server.

## Timing Design

The playback worker should use a background thread and `time.monotonic()` for timing. This is the simplest good fit for the current architecture and should perform fine on the Pi Zero 2 W for the first slice.

This design is preferred over introducing async transport logic right now because:

- the existing app is already organized around straightforward object ownership
- a single playback worker is easy to reason about
- the timing model is easy to test with fakes
- later transport features can still evolve from this base

## State Shape

Playback state should be added to the existing runtime state store. The exact field names can be refined during implementation, but the state should cover:

- `status`: `stopped` or `playing`
- `selected_song_path`
- `song_title`
- `duration_seconds`
- `elapsed_seconds`
- `active_notes`
- `midi_output_enabled`
- `error`

This state should be available through both `GET /api/state` and `GET /api/playback`, with the dedicated playback endpoint returning the most focused payload for the Practice page.

## Testing Strategy

### Unit Tests

- MIDI loader converts a small MIDI file into correctly ordered timed note events
- playback service starts and completes in a stopped, cleared state
- manual Stop clears active playback notes and LEDs
- end-of-song sends final note-offs and clears the strip

### Runtime Tests

- live note events do not change LED output while playback is active
- selected song errors are surfaced cleanly
- playback state is copied into the runtime state store correctly

### Web Tests

- `/api/playback/play` rejects missing song selection cleanly
- `/api/playback/stop` is safe when already stopped
- the Practice page shows playback status and current song information

### Pi Smoke Tests

- selected song plays through the piano over MIDI output
- LEDs follow the notes for a short test file
- Stop clears the strip immediately
- reaching the end clears the strip and does not leave hung notes on the piano

## File Plan

Files expected to change or be added for this first playback slice:

- `src/piano_led/core/models.py`
- `src/piano_led/songs/midi_loader.py`
- `src/piano_led/services/playback.py`
- `src/piano_led/services/runtime.py`
- `src/piano_led/web/server.py`
- `tests/songs/`
- `tests/services/`
- `tests/web/`
- `docs/stages/stage-05-midi-playback.md`

## Success Criteria

This playback slice is complete when:

- a song selected on `/songs` can be played from `/practice`
- the piano sounds through MIDI output during playback when MIDI out is configured
- LEDs follow the song timing
- Stop clears the strip and turns off playback notes on the piano
- end-of-song clears the strip and leaves playback in a stopped state
- the UI shows a clear playback state and any friendly error messages
