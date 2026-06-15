# Stage 03 - Calibration Workflow

## Goal

Correct the generated keymap quickly on the real instrument.

## Build checklist

- start calibration from the current keymap
- optionally show the full keyboard while calibrating
- support "arm next piano key" so a real note press can select the current key
- show the currently mapped LED
- shift mapped LED left or right
- allow lower/higher piano keys to nudge the selected LED one step left/right
- press the same key again to confirm and advance
- persist the updated keymap

## Current checkpoint

- `/keymap` now exposes `Start Calibration`, `Stop Calibration`, `Use Next Piano Key`, manual note selection, shift controls, and confirm
- calibration can optionally show the whole keyboard between edits using the normal note color for white keys and the black-key color for black keys
- once a key is selected, pressing any lower piano key nudges its LED one step left and pressing any higher key nudges it one step right
- pressing the selected key again confirms the mapping, saves it, and restores the whole-keyboard preview if that mode is enabled

## Success criteria

- calibration changes only the selected note
- confirmed mappings survive app restart
