"""Runtime-backed JSON API routes for the FastAPI web UI."""

from __future__ import annotations

from typing import Any

from piano_led.app import Application, apply_midi_ports
from piano_led.midi.input import list_mido_input_ports
from piano_led.midi.output import list_mido_output_ports
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field


class SongSelectionPayload(BaseModel):
    """Request body for changing the selected MIDI song."""

    relative_path: str = Field(min_length=1)


class SongHandConfigPayload(BaseModel):
    """Request body for saving one song's left/right hand mapping."""

    relative_path: str = Field(min_length=1)
    left_hand_tracks: list[int] = Field(default_factory=list)
    right_hand_tracks: list[int] = Field(default_factory=list)
    left_hand_channels: list[int] = Field(default_factory=list)
    right_hand_channels: list[int] = Field(default_factory=list)


class LedSettingsPayload(BaseModel):
    """LED-only settings payload used by the FastAPI settings page."""

    note_color: str | None = None
    black_key_color: str | None = None
    use_black_key_color: bool | None = None
    left_hand_note_color: str | None = None
    left_hand_black_key_color: str | None = None
    right_hand_note_color: str | None = None
    right_hand_black_key_color: str | None = None
    brightness: int | None = Field(default=None, ge=0, le=255)


class UpdateLedSettingsRequest(BaseModel):
    """Request body for persisting LED-related settings."""

    led: LedSettingsPayload


class ApplyMidiPortsPayload(BaseModel):
    """Request body for swapping live MIDI input/output ports."""

    input_port_name: str = ""
    output_port_name: str = ""


def _bad_request(error: Exception) -> HTTPException:
    """Convert runtime validation errors to HTTP 400 responses."""

    return HTTPException(status_code=400, detail=str(error))


def create_api_router(application: Application) -> APIRouter:
    """Create the JSON API router for the current runtime."""

    router = APIRouter()
    runtime = application.runtime

    @router.get("/api/state")
    def state_snapshot() -> dict[str, Any]:
        return runtime.get_state()

    @router.get("/api/settings")
    def settings_snapshot() -> dict[str, Any]:
        return runtime.settings.to_dict()

    @router.post("/api/settings/led")
    def update_led_settings(payload: UpdateLedSettingsRequest) -> dict[str, Any]:
        led_updates = payload.led.model_dump(exclude_none=True)
        return runtime.apply_led_settings(led_updates)

    @router.get("/api/midi/ports")
    def midi_ports() -> dict[str, Any]:
        try:
            return {
                "midi_backend": runtime.settings.midi.backend,
                "input_ports": list_mido_input_ports(),
                "output_ports": list_mido_output_ports(),
                "selected_input_port": runtime.settings.midi.input_port_name,
                "selected_output_port": runtime.settings.midi.output_port_name,
            }
        except ModuleNotFoundError:
            return {
                "midi_backend": runtime.settings.midi.backend,
                "input_ports": [],
                "output_ports": [],
                "selected_input_port": runtime.settings.midi.input_port_name,
                "selected_output_port": runtime.settings.midi.output_port_name,
                "error": "mido backend is not installed on this machine yet.",
            }

    @router.post("/api/midi/apply")
    def apply_midi(payload: ApplyMidiPortsPayload) -> dict[str, Any]:
        try:
            return apply_midi_ports(
                application,
                input_port_name=payload.input_port_name,
                output_port_name=payload.output_port_name,
            )
        except (ModuleNotFoundError, OSError, RuntimeError, ValueError) as error:
            raise _bad_request(error) from error

    @router.post("/api/led/clear")
    def clear_leds() -> dict[str, Any]:
        runtime.clear_leds()
        return {"ok": True, "active_notes": runtime.get_state()["active_notes"]}

    @router.post("/api/led/chase")
    def led_chase() -> dict[str, Any]:
        return runtime.run_chase_test()

    @router.get("/api/songs")
    def list_songs() -> dict[str, list[dict[str, Any]]]:
        return {"songs": runtime.list_songs()}

    @router.get("/api/song-selection")
    def song_selection() -> dict[str, Any]:
        return runtime.get_song_selection_state()

    @router.post("/api/song-selection")
    def select_song(payload: SongSelectionPayload) -> dict[str, Any]:
        try:
            return runtime.select_song(payload.relative_path)
        except ValueError as error:
            raise _bad_request(error) from error

    @router.get("/api/song-hand-config")
    def song_hand_config(relative_path: str = Query(min_length=1)) -> dict[str, Any]:
        try:
            return runtime.get_song_hand_config_state(relative_path)
        except RuntimeError as error:
            raise _bad_request(error) from error

    @router.post("/api/song-hand-config")
    def save_song_hand_config(payload: SongHandConfigPayload) -> dict[str, Any]:
        try:
            return runtime.save_song_hand_config(
                relative_path=payload.relative_path,
                left_hand_tracks=payload.left_hand_tracks,
                right_hand_tracks=payload.right_hand_tracks,
                left_hand_channels=payload.left_hand_channels,
                right_hand_channels=payload.right_hand_channels,
            )
        except (RuntimeError, ValueError) as error:
            raise _bad_request(error) from error

    return router
