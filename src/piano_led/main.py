from __future__ import annotations

import argparse
from pathlib import Path
import time

from piano_led.app import build_application
from piano_led.midi.input import MidoMidiInputPort, list_mido_input_ports
from piano_led.midi.output import list_mido_output_ports


def build_parser() -> argparse.ArgumentParser:
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
    return parser


def main(argv: list[str] | None = None) -> int:
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

    application = build_application(project_root)

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
            midi_input.open()
            print(f"Listening to MIDI input: {midi_input.port_name}")
            if args.seconds is not None:
                time.sleep(max(0.0, args.seconds))
                return 0
            try:
                while True:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                print("Stopped MIDI monitor.")
            return 0
        print("Configured MIDI backend is fake; set midi.backend to 'mido' and a real input port name.")
        return 0

    summary = application.runtime.describe()
    print(summary)
    return 0
