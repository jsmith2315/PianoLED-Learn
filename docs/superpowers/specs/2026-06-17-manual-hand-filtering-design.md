# Manual Hand Filtering Design

## Goal

Add the next playback slice for Piano LED Learn so a selected MIDI song can be played in `both`, `left`, or `right` hand mode using manual per-song hand assignments. The user should be able to define which MIDI tracks and channels belong to each hand for each song, save that setup, and then use it during playback on the Practice page.

This slice also introduces hand-specific LED colors so each note can keep the color of the hand it belongs to, including separate black-key colors for each hand.

## Scope

Included in this slice:

- manual per-song hand assignment
- per-song metadata storage for left and right hand mappings
- playback hand mode selection: `both`, `left`, or `right`
- hand filtering based on assigned MIDI tracks and channels
- hand-aware LED colors, including black-key variants
- hand setup UI on the Songs page
- hand mode selection UI on the Practice page

Not included in this slice:

- automatic hand detection
- guessed assignments
- pause or resume
- loop ranges
- assisted practice where the app plays the other hand
- score or falling-note visual changes

## Future Follow-Up

This design intentionally reserves room for a later enhancement:

- auto-detect hands with manual override

That later feature should live on top of the same per-song metadata model introduced here. The app will eventually be able to suggest hand assignments, let the user correct them, and then save the corrected result back into the same metadata store.

## Recommended Architecture

Three approaches were considered:

1. Per-song metadata with manual assignment
2. Per-session hand assignment entered fresh each time
3. Auto-detect with manual override now

The recommended approach is per-song metadata with manual assignment. It matches the user’s preference, avoids repeated setup work, and creates a stable foundation for both future assisted practice and future auto-detection.

## Data Model

### Song Hand Metadata

Hand assignments should be stored separately from the MIDI file itself under a new metadata folder, for example:

- `data/songs/metadata/<song-name>.json`

Each song metadata file should be keyed to the selected MIDI file path and contain:

- `relative_path`
- `left_hand_tracks`
- `right_hand_tracks`
- `left_hand_channels`
- `right_hand_channels`

All four assignment lists are optional. A song may use track mapping, channel mapping, or both.

### Playback Hand Mode

Runtime playback state should gain:

- `hand_mode`: `both`, `left`, or `right`

This is separate from song metadata. Song metadata describes how to classify notes. Hand mode describes which classified notes are currently played.

### Hand-Aware Event Tagging

Parsed playback events should carry enough metadata to support classification and coloring:

- MIDI track identity
- MIDI channel identity
- assigned hand tag when available: `left`, `right`, or `unassigned`

The filtering and color layers should use the hand tag instead of re-deriving hand ownership repeatedly.

## Behavior

### Hand Assignment Rules

For each selected song, the user can assign one or more tracks and one or more channels to the left hand and right hand.

If both track and channel assignments are present, an event belongs to a hand if it matches either:

- an assigned track for that hand
- an assigned channel for that hand

This keeps setup flexible for real-world MIDI files that may separate hands by track, by channel, or by a mix of both.

### Playback Rules

- `both` plays the full song event list
- `left` plays only events assigned to the left hand
- `right` plays only events assigned to the right hand

If `left` or `right` is selected but that hand has no saved mapping for the current song, playback must not guess. Instead, it should return a friendly error and remain stopped.

`both` must always work, even when no hand metadata exists yet.

### Note Pairing Rule

Filtering must preserve note-on and matching note-off behavior together. The app must never keep a note-on while dropping its note-off, or vice versa. The filtered result must remain a valid playable event stream.

## Hand Colors

The LED settings model should be expanded with hand-specific colors:

- `left_hand_note_color`
- `left_hand_black_key_color`
- `right_hand_note_color`
- `right_hand_black_key_color`

Existing generic note colors should remain as fallbacks for views and tools that are not hand-aware.

### Color Rules

- in `left` mode, notes use left-hand colors
- in `right` mode, notes use right-hand colors
- in `both` mode, each note uses the color of the hand it belongs to
- black keys use the black-key color for their assigned hand

This means color rendering depends on hand tagging, not just note number.

## UI Design

### Songs Page

The Songs page should gain a hand setup section for the currently selected song:

- `Left Hand Source`
- `Right Hand Source`
- one or more track checkboxes or selectors
- one or more channel checkboxes or selectors
- `Save Hand Setup`

The page should inspect the selected MIDI file and show which tracks and channels are available for assignment.

This page is the right place for song-specific setup because it already owns song selection and per-song configuration fits naturally here.

### Practice Page

The Practice page should gain:

- `Playback Hand Mode` selector with `Both`, `Left`, and `Right`

Playback should use the selected hand mode immediately. The page should continue to show current playback state and also reflect the selected hand mode in that state.

## Engine Design

The playback engine should filter events before the worker thread starts timing playback. This is better than deciding hand ownership during every timing tick.

The flow should be:

1. load parsed song events with track and channel metadata
2. load saved hand metadata for the selected song
3. classify events by hand
4. apply selected hand mode to produce the filtered playback event list
5. start playback on that filtered list

This keeps playback timing simple and makes future features easier because playback works from a prepared event list instead of mixing scheduling with classification logic.

## Storage and API

### New Storage Module

Add a small metadata storage layer for song hand configuration. It should:

- save per-song metadata
- load metadata for a song
- return empty/default metadata when none exists yet

### New API Endpoints

The web layer should gain:

- `GET /api/song-hand-config`
- `POST /api/song-hand-config`
- a small runtime endpoint or state field for `hand_mode`

The dedicated hand-config API should support the Songs page editor. Playback state should expose the current `hand_mode` for Practice.

## Error Handling

Friendly errors should cover:

- `left` or `right` mode selected with no saved mapping for that hand
- saved metadata references tracks or channels that no longer exist in the file
- MIDI summary cannot be read for the selected song

Errors should be readable to the user and should not crash playback, the runtime, or the web UI.

## Verification

By user preference, verification for this slice should rely on manual Pi testing rather than unit tests.

Expected Pi checks:

1. select a song with separated hands
2. save left and right track or channel assignments on the Songs page
3. choose `Left` mode on Practice and confirm only left-hand notes sound and light
4. choose `Right` mode on Practice and confirm only right-hand notes sound and light
5. choose `Both` mode and confirm full playback still works
6. confirm simultaneous left and right notes each keep their own hand color
7. confirm black-key notes use the black-key color for their hand
8. try `Left` or `Right` on a song with no hand setup and confirm the app shows a friendly error

## Success Criteria

This slice is complete when:

- each song can store manual left/right hand assignments
- Practice playback can switch between `both`, `left`, and `right`
- filtered playback sounds and lights only the selected hand when requested
- `both` mode keeps per-note hand colors
- left/right hand black keys use their own black-key colors
- missing hand mappings fail safely with a friendly message
- the design clearly preserves room for later auto-detect with manual override
