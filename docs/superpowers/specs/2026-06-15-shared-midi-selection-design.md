## Shared MIDI Selection Design

### Goal

Add the first slice of Stage 5 by making MIDI file selection shared across the app. If a song is selected on the Listen page, the Learning page should show that same selection automatically during the current runtime session.

### Scope

This slice adds shared song browsing and selection only. It does not yet add MIDI parsing, transport controls, playback scheduling, or learning-mode playback behavior.

### Requirements

- Scan `data/songs/midi` for available `.mid` and `.midi` files.
- Store one runtime-wide selected MIDI file.
- Show and change that selection from the `/songs` page.
- Show the current selection on the `/practice` page.
- Keep the selection session-only for now.
- Do not write the selected song into `settings.json` or `settings.local.json`.

### Recommended Approach

Use a small backend song library plus a runtime-owned selected-song field.

This keeps the browser UI thin, makes `/songs` and `/practice` consistent, and gives Stage 5 a clean place to connect real playback later. It also avoids pushing selection logic into page-local JavaScript where the pages could drift out of sync.

### Architecture Changes

#### Song library

Add a small songs module responsible for scanning the MIDI folder and returning user-facing song entries. Each entry should include:

- file name
- relative path from `data/songs/midi`
- simple display title based on file name

The scan should ignore non-MIDI files.

#### Runtime state

Add a runtime-owned `selected_song_path` field as the single source of truth for the current song selection. This value should live only in memory for this stage.

The runtime should expose:

- current song selection
- available song list
- a method to change the selected song after validating it exists in the current library

#### Web layer

Add API endpoints:

- `GET /api/songs`
- `GET /api/song-selection`
- `POST /api/song-selection`

Update `/songs` to show:

- available MIDI files
- current selected song
- a control to choose a song

Update `/practice` to show:

- current selected song
- a simple note that playback/learning controls will attach here next

### Data Flow

1. Browser requests available songs from `/api/songs`.
2. Browser requests the current selection from `/api/song-selection`.
3. User selects a MIDI file on `/songs`.
4. Browser posts the chosen relative path to `/api/song-selection`.
5. Runtime validates the selection against the current song library and stores it in memory.
6. `/practice` reads the same runtime state and shows the selected song without extra user input.

### Error Handling

- If no MIDI files exist, `/api/songs` returns an empty list and the pages show a friendly empty state.
- If the user posts a path that is not in the scanned library, the API returns a clear validation error.
- If the current selection becomes invalid because files changed during runtime, the runtime should clear the selection on the next validation or refresh.

### Testing

Add unit and web tests for:

- scanning only `.mid` and `.midi` files
- returning stable song metadata from the library
- updating runtime selected-song state
- rejecting invalid song selections
- showing the shared selected song on both `/songs` and `/practice`
- keeping song selection out of persisted settings files

### Out of Scope

- MIDI event parsing
- playback transport
- pause, resume, stop, or seek
- hand filtering
- LED playback rendering
- MIDI output to the piano

### Acceptance Criteria

- A MIDI file selected on `/songs` is immediately shown as the selected file on `/practice`.
- The selected file is shared across pages during the current app session.
- Restarting the app clears the selection.
- The song list is sourced from `data/songs/midi`.
- Invalid selections are rejected cleanly.
