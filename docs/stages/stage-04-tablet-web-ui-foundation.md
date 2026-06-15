# Stage 04 - Tablet Web UI Foundation

## Goal

Expose the runtime through a Pi-hosted browser interface.

## Build checklist

- serve a home page and settings page
- expose state and settings APIs
- expose LED clear and chase actions
- expose keymap generation and calibration actions
- expose whole-keyboard keymap preview and whole-map shift actions
- show live runtime state in the browser while the Pi is running with live MIDI enabled
- make it usable from an Android tablet browser

## Success criteria

- browser can read current state
- browser can trigger clear/chase/calibration actions
- browser can update settings and generate a keymap
- browser can preview the entire generated keymap and shift it left/right before fine tuning
- browser reflects active notes and calibration arm state without needing a manual refresh
