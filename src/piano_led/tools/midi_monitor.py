from __future__ import annotations

from piano_led.midi.input import FakeMidiInputPort, MidoMidiInputPort


def build_monitor() -> FakeMidiInputPort:
    return FakeMidiInputPort()


def build_live_monitor(port_name: str) -> MidoMidiInputPort:
    return MidoMidiInputPort(port_name=port_name)
