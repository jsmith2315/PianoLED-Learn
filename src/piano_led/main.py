"""Command-line entrypoints for local development and Raspberry Pi operation."""

from __future__ import annotations

import argparse
from pathlib import Path
import time
import json
from wsgiref.simple_server import make_server

from piano_led.app import build_application
from piano_led.web.server import create_web_app
from piano_led.midi.input import MidoMidiInputPort, list_mido_input_ports
from piano_led.midi.output import list_mido_output_ports


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level CLI parser."""

    parser = argparse.ArgumentParser(description="Piano LED Learn command line")
    parser.add_argument("--project-root", default=".", help="Project root containing data/ and config files")

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="Print runtime summary")
    subparsers.add_parser("midi-list-ports", help="List available MIDI input and output ports")

    led_chase = subparsers.add_parser("led-chase", help="Run a short LED chase animation")
    led_chase.add_argument("--steps", type=int, default=10)
    led_chase.add_argument("--delay-ms", type=float, default=75.0, help="Delay between chase frames in milliseconds")

    subparsers.add_parser("led-clear", help="Clear the LED strip")
    midi_monitor = subparsers.add_parser("midi-monitor", help="Subscribe to the configured live MIDI input")
    midi_monitor.add_argument("--seconds", type=float, default=None, help="Optional bounded monitoring duration")
    run_live = subparsers.add_parser("run-live", help="Run the live piano-to-LED loop")
    run_live.add_argument("--seconds", type=float, default=None, help="Optional bounded runtime duration")
    keymap_generate = subparsers.add_parser("keymap-generate", help="Generate and save the base keymap")
    keymap_generate.add_argument("--total-leds", type=int, required=True)
    keymap_generate.add_argument("--first-led", type=int, required=True)
    keymap_generate.add_argument("--direction", choices=["left_to_right", "right_to_left"], required=True)
    web_serve = subparsers.add_parser("web-serve", help="Serve the browser UI for tablet access")
    web_serve.add_argument("--host", default="0.0.0.0")
    web_serve.add_argument("--port", type=int, default=8080)
    web_serve.add_argument("--seconds", type=float, default=None, help="Optional bounded runtime duration")
    web_serve.add_argument("--with-live", action="store_true", help="Also open the configured live MIDI input")
    return parser


def run_midi_loop(midi_input: MidoMidiInputPort, seconds: float | None) -> int:
    """Open the configured MIDI input and keep the process alive."""

    midi_input.open()
    print(f"Listening to MIDI input: {midi_input.port_name}")
    if seconds is not None:
        time.sleep(max(0.0, seconds))
        return 0
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Stopped MIDI monitor.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the requested CLI command and return a process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv or [])
    project_root = Path(args.project_root).resolve()

    if args.command == "midi-list-ports":
        try:
            print("MIDI inputs:")
            for name in list_mido_input_ports():
                print(f"- {name}")
            print("MIDI outputs:")
            for name in list_mido_output_ports():
                print(f"- {name}")
        except ModuleNotFoundError:
            print("mido backend is not installed yet on this machine.")
        return 0

    initialize_leds = args.command in {"led-chase", "led-clear", "midi-monitor", "run-live", "web-serve", None}
    application = build_application(project_root, initialize_leds=initialize_leds)

    if args.command == "keymap-generate":
        payload = application.runtime.generate_keymap(
            total_leds=args.total_leds,
            first_led=args.first_led,
            direction=args.direction,
        )
        print(json.dumps(payload, indent=2))
        return 0

    if args.command == "web-serve":
        if args.with_live:
            midi_input = application.midi_input
            if isinstance(midi_input, MidoMidiInputPort):
                midi_input.open()
                print(f"Listening to MIDI input: {midi_input.port_name}")
            else:
                print("Configured MIDI backend is fake; web server will run without live MIDI input.")
        app = create_web_app(application.runtime)
        server = make_server(args.host, args.port, app)
        server.timeout = 0.5
        print(f"Serving Piano LED Learn at http://{args.host}:{args.port}")
        start = time.monotonic()
        try:
            while True:
                server.handle_request()
                if args.seconds is not None and (time.monotonic() - start) >= max(0.0, args.seconds):
                    break
        except KeyboardInterrupt:
            print("Stopped web server.")
        finally:
            server.server_close()
        return 0

    if args.command == "led-chase":
        for _ in range(args.steps):
            application.runtime.handle_chase_step()
            time.sleep(max(0.0, args.delay_ms) / 1000.0)
        print(f"Ran {args.steps} chase steps.")
        return 0

    if args.command == "led-clear":
        application.runtime.clear_leds()
        print("LEDs cleared.")
        return 0

    if args.command == "midi-monitor":
        midi_input = application.midi_input
        if isinstance(midi_input, MidoMidiInputPort):
            return run_midi_loop(midi_input, args.seconds)
        print("Configured MIDI backend is fake; set midi.backend to 'mido' and a real input port name.")
        return 0

    if args.command == "run-live":
        print(application.runtime.describe())
        midi_input = application.midi_input
        if isinstance(midi_input, MidoMidiInputPort):
            return run_midi_loop(midi_input, args.seconds)
        print("Configured MIDI backend is fake; set midi.backend to 'mido' and a real input port name.")
        return 0

    summary = application.runtime.describe()
    print(summary)
    return 0
