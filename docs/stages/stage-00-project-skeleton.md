# Stage 00 - Project Skeleton

## Goal

Create a clean Python project that runs without Pi hardware.

## Build checklist

- create package layout under `src/piano_led/`
- add local-dev import support
- create fake LED and fake MIDI layers
- create settings and keymap storage folders
- add baseline unit tests
- make `python -m piano_led` start cleanly

## Success criteria

- tests run on a normal computer
- fake runtime can light pixels in memory
- no Pi-specific dependency is required for the first run

