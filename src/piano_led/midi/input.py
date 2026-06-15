"""Live MIDI input abstractions and mido-backed adapters."""

from __future__ import annotations

import importlib
from collections.abc import Callable

from piano_led.core.models import NoteEvent


class MidiInputPort:
    """Base note-event source that listeners can subscribe to."""
    def __init__(self) -> None:
        self._listeners: list[Callable[[NoteEvent], None]] = []

    def subscribe(self, listener: Callable[[NoteEvent], None]) -> None:
        self._listeners.append(listener)

    def emit(self, event: NoteEvent) -> None:
        for listener in self._listeners:
            listener(event)


class FakeMidiInputPort(MidiInputPort):
    """In-memory MIDI input used by tests and local development."""


class MidoMidiInputPort(MidiInputPort):
    """Real MIDI input wrapper backed by the ``mido`` library."""
    def __init__(self, port_name: str, mido_module=None) -> None:
        super().__init__()
        self.port_name = port_name
        self._mido = mido_module
        self._handle = None

    @property
    def mido(self):
        if self._mido is None:
            self._mido = importlib.import_module("mido")
        return self._mido

    def open(self) -> None:
        self._handle = self.mido.open_input(self.port_name, callback=self._handle_message)

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def _handle_message(self, message) -> None:
        if getattr(message, "type", None) == "note_on":
            event = NoteEvent.note_on(note=message.note, velocity=message.velocity, source=self.port_name)
            self.emit(event)
        elif getattr(message, "type", None) == "note_off":
            event = NoteEvent.note_off(note=message.note, source=self.port_name)
            self.emit(event)


def list_mido_input_ports(mido_module=None) -> list[str]:
    """Return deduplicated visible MIDI input port names."""
    module = mido_module or importlib.import_module("mido")
    seen: set[str] = set()
    unique: list[str] = []
    for name in module.get_input_names():
        if name not in seen:
            seen.add(name)
            unique.append(name)
    return unique
