"""Live MIDI output abstractions and mido-backed adapters."""

from __future__ import annotations

import importlib

from piano_led.core.models import NoteEvent


class MidiOutputPort:
    """Base MIDI output interface."""
    def open(self) -> None:
        return None

    def send(self, event: NoteEvent) -> None:
        raise NotImplementedError


class FakeMidiOutputPort(MidiOutputPort):
    """In-memory MIDI output used by tests and local development."""
    def __init__(self) -> None:
        self.sent_events: list[NoteEvent] = []

    def send(self, event: NoteEvent) -> None:
        self.sent_events.append(event)


class MidoMidiOutputPort(MidiOutputPort):
    """Real MIDI output wrapper backed by the ``mido`` library."""
    def __init__(self, port_name: str, mido_module=None) -> None:
        self.port_name = port_name
        self._mido = mido_module
        self._handle = None

    @property
    def mido(self):
        if self._mido is None:
            self._mido = importlib.import_module("mido")
        return self._mido

    def open(self) -> None:
        self._handle = self.mido.open_output(self.port_name)

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def send(self, event: NoteEvent) -> None:
        if self._handle is None:
            raise RuntimeError("MIDI output port is not open")
        if event.event_type == "note_on":
            message = self.mido.Message("note_on", note=event.note, velocity=event.velocity)
        elif event.event_type == "note_off":
            message = self.mido.Message("note_off", note=event.note, velocity=0)
        else:
            raise ValueError(f"Unsupported MIDI event type: {event.event_type}")
        self._handle.send(message)


def list_mido_output_ports(mido_module=None) -> list[str]:
    """Return deduplicated visible MIDI output port names."""
    module = mido_module or importlib.import_module("mido")
    seen: set[str] = set()
    unique: list[str] = []
    for name in module.get_output_names():
        if name not in seen:
            seen.add(name)
            unique.append(name)
    return unique
