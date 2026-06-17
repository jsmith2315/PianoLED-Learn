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
- shared MIDI song discovery from data/songs/midi
- one runtime-wide selected MIDI file
- /songs picker and /practice shared selection display
- session-only selection state for the current app run

## Playback first slice implemented
- /practice can play the selected MIDI from the beginning
- playback sends note events to LEDs
- playback sends note events to MIDI output when configured
- playback owns the strip while active
- stop and end-of-song both clear LEDs and send note-offs

## Manual hand filtering implemented
- Songs page can save left/right hand assignment by track and channel
- Practice page can switch between `both`, `left`, and `right`
- playback uses hand-specific LED colors
- black keys use hand-specific black-key colors
- missing hand mappings fail with a friendly error

## Pi smoke test
1. `git pull`
2. `python3 -m piano_led status`
3. `sudo python3 -m piano_led web-serve --host 0.0.0.0 --port 8080 --with-live`
4. Open `/songs`, select a MIDI file, then open `/practice`.
5. Press `Play Selected Song` and confirm the piano sounds and LEDs follow the notes.
6. Press `Stop` and confirm the strip clears immediately.
7. Let the song finish and confirm the strip clears with no hung notes.

## Pi smoke test for hand filtering
1. `git pull`
2. `sudo python3 -m piano_led web-serve --host 0.0.0.0 --port 8080 --with-live`
3. Open `/songs` and select a song with separated hands.
4. Save left and right hand track or channel assignments.
5. Open `/practice` and test `Both`, `Left`, and `Right`.
6. Confirm left and right notes keep their own hand colors in `Both`.
7. Confirm black keys use the black-key color for their hand.
8. Try `Left` or `Right` without a saved mapping on another song and confirm the app shows a friendly error.
