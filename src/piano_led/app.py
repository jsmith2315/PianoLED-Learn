"""Application factory and backend wiring for Piano LED Learn."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from piano_led.config.settings import AppSettings, SettingsStore
from piano_led.keymap.generator import KeymapGenerator
from piano_led.keymap.storage import KeymapStore
from piano_led.leds.driver_fake import FakeLedDriver
from piano_led.leds.driver_rpi_ws281x import create_rpi_led_driver
from piano_led.midi.input import FakeMidiInputPort, MidoMidiInputPort
from piano_led.midi.output import FakeMidiOutputPort, MidoMidiOutputPort
from piano_led.services.runtime import PianoLedRuntime
from piano_led.services.state_store import StateStore


@dataclass
class Application:
    """Container for the runtime and currently selected backends."""

    runtime: PianoLedRuntime
    settings_store: SettingsStore
    keymap_store: KeymapStore
    state_store: StateStore
    midi_input: FakeMidiInputPort | MidoMidiInputPort
    midi_output: FakeMidiOutputPort | MidoMidiOutputPort


def build_application(project_root: Path | None = None, initialize_leds: bool = True) -> Application:
    """Build the configured runtime and I/O adapters.

    Non-hardware commands can pass ``initialize_leds=False`` to avoid touching
    the real WS281X driver while still reading settings and keymaps.
    """

    root = project_root or Path.cwd()
    settings_path = root / "data" / "settings" / "settings.json"
    local_settings_path = root / "data" / "settings" / "settings.local.json"
    keymap_path = root / "data" / "keymaps" / "default_88.json"

    settings_store = SettingsStore(settings_path, local_path=local_settings_path)
    settings = settings_store.load()
    keymap_store = KeymapStore(keymap_path)
    keymap = keymap_store.load()
    if not keymap.note_to_led:
        keymap = KeymapGenerator().generate(
            total_leds=settings.led.total_leds,
            first_led=settings.led.default_first_led,
            direction=settings.led.strip_direction,
        )
        keymap_store.save(keymap)

    if initialize_leds and settings.led.backend == "rpi_ws281x":
        led_driver = create_rpi_led_driver(settings)
    else:
        led_driver = FakeLedDriver(total_leds=settings.led.total_leds)

    if settings.midi.backend == "mido" and settings.midi.input_port_name:
        midi_input = MidoMidiInputPort(port_name=settings.midi.input_port_name)
    else:
        midi_input = FakeMidiInputPort()

    if settings.midi.backend == "mido" and settings.midi.output_port_name:
        midi_output = MidoMidiOutputPort(port_name=settings.midi.output_port_name)
    else:
        midi_output = FakeMidiOutputPort()

    state_store = StateStore()
    runtime = PianoLedRuntime(
        settings=settings,
        keymap=keymap,
        led_driver=led_driver,
        settings_store=settings_store,
        keymap_store=keymap_store,
        state_store=state_store,
    )
    runtime.attach_midi_input(midi_input)
    return Application(
        runtime=runtime,
        settings_store=settings_store,
        keymap_store=keymap_store,
        state_store=state_store,
        midi_input=midi_input,
        midi_output=midi_output,
    )
