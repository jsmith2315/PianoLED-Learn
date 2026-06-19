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
from piano_led.songs.hand_config import SongHandConfigStore
from piano_led.songs.library import SongLibrary


@dataclass
class Application:
    """Container for the runtime and currently selected backends."""

    runtime: PianoLedRuntime
    settings_store: SettingsStore
    keymap_store: KeymapStore
    state_store: StateStore
    midi_input: FakeMidiInputPort | MidoMidiInputPort
    midi_output: FakeMidiOutputPort | MidoMidiOutputPort


def create_midi_input(settings: AppSettings) -> FakeMidiInputPort | MidoMidiInputPort:
    """Create the configured MIDI input backend from current settings."""

    if settings.midi.backend == "mido" and settings.midi.input_port_name:
        return MidoMidiInputPort(port_name=settings.midi.input_port_name)
    return FakeMidiInputPort()


def create_midi_output(settings: AppSettings) -> FakeMidiOutputPort | MidoMidiOutputPort:
    """Create the configured MIDI output backend from current settings."""

    if settings.midi.backend == "mido" and settings.midi.output_port_name:
        return MidoMidiOutputPort(port_name=settings.midi.output_port_name)
    return FakeMidiOutputPort()


def apply_midi_ports(application: Application, input_port_name: str, output_port_name: str) -> dict:
    """Swap live MIDI ports, persist them, and return the active selection."""

    settings = application.runtime.settings
    draft_settings = AppSettings.from_dict(settings.to_dict())
    draft_settings.midi.backend = "mido"
    draft_settings.midi.input_port_name = input_port_name.strip()
    draft_settings.midi.output_port_name = output_port_name.strip()

    midi_input = create_midi_input(draft_settings)
    midi_output = create_midi_output(draft_settings)

    try:
        if isinstance(midi_input, MidoMidiInputPort):
            midi_input.open()
        if isinstance(midi_output, MidoMidiOutputPort):
            midi_output.open()
    except Exception:
        midi_input.close()
        midi_output.close()
        raise

    settings.midi.backend = draft_settings.midi.backend
    settings.midi.input_port_name = draft_settings.midi.input_port_name
    settings.midi.output_port_name = draft_settings.midi.output_port_name

    application.runtime.replace_midi_input(midi_input)
    application.runtime.replace_midi_output(midi_output)
    application.midi_input = midi_input
    application.midi_output = midi_output
    application.settings_store.save(settings)
    application.runtime.refresh_state()
    return {
        "midi_backend": settings.midi.backend,
        "input_port_name": settings.midi.input_port_name,
        "output_port_name": settings.midi.output_port_name,
    }


def build_application(project_root: Path | None = None, initialize_leds: bool = True) -> Application:
    """Build the configured runtime and I/O adapters.

    Non-hardware commands can pass ``initialize_leds=False`` to avoid touching
    the real WS281X driver while still reading settings and keymaps.
    """

    root = project_root or Path.cwd()
    settings_path = root / "data" / "settings" / "settings.json"
    local_settings_path = root / "data" / "settings" / "settings.local.json"
    keymap_path = root / "data" / "keymaps" / "default_88.json"
    songs_root = root / "data" / "songs" / "midi"
    song_hand_config_root = root / "data" / "songs" / "metadata"

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

    midi_input = create_midi_input(settings)
    midi_output = create_midi_output(settings)

    state_store = StateStore()
    song_library = SongLibrary(songs_root)
    song_hand_config_store = SongHandConfigStore(song_hand_config_root)
    runtime = PianoLedRuntime(
        settings=settings,
        keymap=keymap,
        led_driver=led_driver,
        settings_store=settings_store,
        keymap_store=keymap_store,
        state_store=state_store,
        song_library=song_library,
        midi_output=midi_output,
        song_hand_config_store=song_hand_config_store,
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
