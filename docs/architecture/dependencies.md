# Dependency Compatibility Notes

## Current implementation policy

The current implemented foundation slice is intentionally **standard-library only** on the Python side.

That means stages 0-4 do not currently require:

- Flask
- FastAPI
- aiohttp
- mido
- python-rtmidi
- music21

This keeps local development simple and avoids locking the project to a library that later turns out to be awkward on a Raspberry Pi Zero 2 W.

## Approved Python 3.11 / Pi-friendly libraries for later stages

### `rpi-ws281x==5.0.0`

Why it is approved:

- PyPI metadata says it requires **Python >=3.6**
- the project is specifically for Raspberry Pi WS281X/SK6812 LED control
- the release history notes Pi Zero 2 W support was added in the 4.3.x line

How we plan to use it:

- only on the Pi hardware driver path
- not during normal laptop development
- ideally from a pinned, known-good wheel for `cp311` on `linux_armv7l`

Source:

- [PyPI: rpi-ws281x](https://pypi.org/project/rpi-ws281x/)

### `mido==1.3.3`

Why it is approved:

- PyPI metadata says it requires **Python 3.7+**
- classifiers explicitly include **Python 3.11**
- it supports both MIDI messages and MIDI files, which fits stages 5-6 well

How we plan to use it:

- MIDI message model
- MIDI file loading and playback scheduling
- optional port backend integration

Source:

- [PyPI: mido](https://pypi.org/project/mido/)

## Optional but not yet required

### `python-rtmidi`

Why it is not required yet:

- PyPI metadata says it requires **Python 3.8+** and includes **Python 3.11**
- it is a good candidate for live MIDI input/output
- but it is a compiled binding, so the Pi installation path is more sensitive than pure-Python packages

Decision:

- keep the runtime backend-agnostic for now
- validate this backend on the Pi before making it the default live-MIDI dependency

Source:

- [PyPI: python-rtmidi](https://pypi.org/project/python-rtmidi/)

## Libraries we are intentionally avoiding

### Heavy Python score libraries in the first pass

Examples:

- `music21`
- large notation/rendering stacks on the backend

Reason:

- they add weight and complexity on a Pi Zero 2 W
- falling notes and score rendering can be pushed mostly to the browser later

## Practical install plan

When we reach the Pi-only stages:

1. keep local development on the standard-library/fake-driver path
2. install `mido` for file parsing and portable MIDI objects
3. install `rpi-ws281x` from a pinned wheel for Python 3.11 on the Pi
4. validate the preferred live-MIDI backend on-device before making it mandatory

