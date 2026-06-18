"""HTML page routes for the FastAPI web UI."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from piano_led.services.runtime import PianoLedRuntime


def create_page_router(runtime: PianoLedRuntime) -> APIRouter:
    """Create the HTML page router for the current runtime."""

    router = APIRouter()
    templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

    @router.get("/", response_class=HTMLResponse)
    def home(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "page_title": "Piano LED Learn",
                "runtime_summary": runtime.describe(),
            },
        )

    return router
