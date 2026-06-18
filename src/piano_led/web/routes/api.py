"""Runtime-backed JSON API routes for the FastAPI web UI."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from piano_led.services.runtime import PianoLedRuntime


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


def _bad_request(error: Exception) -> HTTPException:
    """Convert runtime validation errors to HTTP 400 responses."""

    return HTTPException(status_code=400, detail=str(error))


def create_api_router(runtime: PianoLedRuntime) -> APIRouter:
    """Create the JSON API router for the current runtime."""

    router = APIRouter()

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
