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

### `fastapi`

Why it is approved:

- PyPI metadata says it requires **Python >=3.10**
- classifiers explicitly include **Python 3.11**
- it provides a clean Python-first path for HTML routes, JSON APIs, templates, static files, and later WebSocket work

How we plan to use it:

- page routing for the Pi-hosted browser UI
- JSON API endpoints used by Alpine.js
- a cleaner migration path away from large inline HTML strings in Python modules

Source:

- [PyPI: fastapi](https://pypi.org/project/fastapi/)

### `uvicorn`

Why it is approved:

- PyPI metadata says it requires **Python >=3.10**
- classifiers explicitly include **Python 3.11**
- it is the minimal ASGI server companion for FastAPI and supports HTTP and WebSockets

How we plan to use it:

- serve the FastAPI app from the existing `python3 -m piano_led web-serve` command
- keep the Pi launch flow simple while moving from WSGI to ASGI

Source:

- [PyPI: uvicorn](https://pypi.org/project/uvicorn/)

### `jinja2`

Why it is approved:

- PyPI metadata says it requires **Python >=3.7**
- it is a stable Python templating engine widely used with FastAPI and Flask
- it lets us move page markup out of large Python string literals

How we plan to use it:

- shared base layout and page templates
- incremental migration of `/songs`, `/settings`, `/keymap`, and `/practice`

Source:

- [PyPI: Jinja2](https://pypi.org/project/Jinja2/)

### `tailwindcss`

Why it is approved:

- it is only a frontend build dependency and does not affect runtime MIDI or LED logic
- it gives reusable styling utilities without requiring a heavier frontend framework
- the old project already proved this styling approach can work well for the browser UI

How we plan to use it:

- build `src/piano_led/web/static/css/tailwind.css` from a small source file
- keep the compiled CSS in the app's static assets
- run `npm run build-css` on the Pi before launching the updated UI

Decision:

- treat Tailwind as a build-time tool only
- keep runtime browser behavior in Alpine.js and backend behavior in Python

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
