import types
import unittest

from piano_led.core.models import NoteEvent
from piano_led.midi.input import MidoMidiInputPort
from piano_led.midi.output import MidoMidiOutputPort


class FakeInputHandle:
    def __init__(self, name, callback):
        self.name = name
        self.callback = callback
        self.closed = False

    def close(self):
        self.closed = True


class FakeOutputHandle:
    def __init__(self, name):
        self.name = name
        self.sent = []
        self.closed = False

    def send(self, message):
        self.sent.append(message)

    def close(self):
        self.closed = True


class MidoPortTests(unittest.TestCase):
    def test_mido_input_converts_messages_to_note_events(self) -> None:
        opened = {}

        def open_input(name, callback):
            handle = FakeInputHandle(name, callback)
            opened["handle"] = handle
            return handle

        fake_mido = types.SimpleNamespace(
            open_input=open_input,
            Message=lambda kind, **kwargs: types.SimpleNamespace(type=kind, **kwargs),
        )

        port = MidoMidiInputPort(port_name="Piano", mido_module=fake_mido)
        received = []
        port.subscribe(received.append)
        port.open()

        opened["handle"].callback(types.SimpleNamespace(type="note_on", note=60, velocity=100))
        opened["handle"].callback(types.SimpleNamespace(type="note_off", note=60, velocity=0))

        self.assertEqual(received[0], NoteEvent.note_on(note=60, velocity=100, source="Piano"))
        self.assertEqual(received[1], NoteEvent.note_off(note=60, source="Piano"))

    def test_mido_output_sends_note_events_as_mido_messages(self) -> None:
        created_messages = []

        def message(kind, **kwargs):
            payload = types.SimpleNamespace(type=kind, **kwargs)
            created_messages.append(payload)
            return payload

        output_handle = FakeOutputHandle("Piano Out")
        fake_mido = types.SimpleNamespace(
            open_output=lambda name: output_handle,
            Message=message,
        )

        port = MidoMidiOutputPort(port_name="Piano Out", mido_module=fake_mido)
        port.open()
        port.send(NoteEvent.note_on(note=64, velocity=80, source="runtime"))
        port.send(NoteEvent.note_off(note=64, source="runtime"))

        self.assertEqual(created_messages[0].type, "note_on")
        self.assertEqual(created_messages[0].note, 64)
        self.assertEqual(output_handle.sent[1].type, "note_off")
