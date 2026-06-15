# Stage 03 - Calibration Workflow

## Goal

Correct the generated keymap quickly on the real instrument.

## Build checklist

- start calibration from the current keymap
- support "arm next piano key" so a real note press can select the current key
- show the currently mapped LED
- shift mapped LED left or right
- press the same key again to confirm and advance
- persist the updated keymap

## Current checkpoint

- `/keymap` now exposes `Start Calibration`, `Use Next Piano Key`, manual note selection, shift controls, and confirm
- the runtime tracks `awaiting_note` so the next live `note_on` can either select a new calibration key or confirm the already selected one
- confirming a note clears the temporary LED highlight and saves the keymap update

## Success criteria

- calibration changes only the selected note
- confirmed mappings survive app restart
