# Stage 05 - MIDI Playback

## Goal

Load MIDI files, play them back, and light the LEDs in sync.

## Planned steps

- add song library scanning
- add MIDI-file parsing/loading
- add transport state and scheduling
- add playback hand filters
- optionally send playback back to the piano

## First implemented slice

- shared MIDI song discovery from `data/songs/midi`
- one runtime-wide selected MIDI file
- `/songs` picker and `/practice` shared selection display
- session-only selection state for the current app run
