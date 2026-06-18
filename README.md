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

## Install

Use Python 3.11+:

```powershell
python -m pip install -e .
```

For the new web UI stack you will also need the frontend build tools:

```powershell
npm install
npm run build-css
```

## Run locally

Use the bundled Python runtime or your own Python 3.11+:

```powershell
python -m unittest discover -s tests -v
python -m piano_led
python -m piano_led web-serve --host 127.0.0.1 --port 8080
```

## Run on the Pi

After pulling new changes on the Pi:

```bash
cd ~/PianoLED-Learn
python3 -m pip install -e .
npm install
npm run build-css
sudo python3 -m piano_led web-serve --host 0.0.0.0 --port 8080 --with-live
```

If a change only touches the web styling, rebuild CSS again before launching:

```bash
npm run build-css
```

## Docs

- [Architecture Overview](docs/architecture/overview.md)
- [Stage Index](docs/stages/README.md)
