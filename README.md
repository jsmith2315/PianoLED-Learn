# Piano LED Learn

Ground-up rebuild of a piano LED visualizer and learning tool for Raspberry Pi Zero 2 W, WS2812B LEDs, USB MIDI pianos, and an Android-tablet browser UI.

## Current status

This repo currently implements the early foundation:

- project skeleton and local-dev runtime
- fake MIDI and LED drivers
- note-to-LED lighting with black-key color support
- settings and keymap JSON storage
- generated base keymaps
- calibration state machine
- minimal Pi-hosted web/API layer for settings, state, LED tools, and calibration

## Run locally

Use the bundled Python runtime or your own Python 3.11+:

```powershell
python -m unittest discover -s tests -v
python -m piano_led
```

## Docs

- [Architecture Overview](docs/architecture/overview.md)
- [Stage Index](docs/stages/README.md)

