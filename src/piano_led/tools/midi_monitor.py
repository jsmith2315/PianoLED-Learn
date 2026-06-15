"""Helpers for constructing fake and live MIDI monitors."""

from __future__ import annotations

from piano_led.midi.input import FakeMidiInputPort, MidoMidiInputPort


def build_monitor() -> FakeMidiInputPort:
    """Return a fake MIDI monitor used by tests and local development."""

    return FakeMidiInputPort()


def build_live_monitor(port_name: str) -> MidoMidiInputPort:
    """Return a live MIDO-backed monitor for a named MIDI port."""

    return MidoMidiInputPort(port_name=port_name)
