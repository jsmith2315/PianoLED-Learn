# Piano LED Learn Architecture

## Goal

Keep the project easy to learn and extend by separating it into:

1. core models and note/key helpers
2. MIDI services
3. LED rendering and drivers
4. keymap generation and calibration
5. runtime state and event wiring
6. web UI and API
7. later playback and learning modules

## Runtime shape

- `StateStore` is the read-mostly source of truth for UI-visible state.
- `PianoLedRuntime` coordinates note events, settings, keymaps, and LED rendering.
- `LedDriver` abstracts real hardware vs fake development/testing behavior.
- `MidiInputPort` and `MidiOutputPort` abstract live MIDI devices.
- `CalibrationSession` owns the “select key, adjust LED, confirm” workflow.

## Data layout

- `data/settings/settings.json` stores runtime settings.
- `data/keymaps/*.json` stores generated and calibrated note-to-LED maps.
- `data/songs/` holds MIDI and MusicXML assets for later stages.
- `docs/stages/` contains the staged implementation roadmap in editable files.

## Early-stage implementation boundary

The current implementation intentionally focuses on stages 0-4:

- local-dev app startup
- realtime note lighting
- generated keymaps
- calibration flow
- minimal browser control surface

Playback, looping, assisted practice, falling notes, and score rendering are planned next, but are not yet implemented in this first foundation slice.

