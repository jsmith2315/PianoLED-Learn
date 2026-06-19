"""FastAPI application factory for Piano LED Learn."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.wsgi import WSGIMiddleware

from piano_led.app import Application
from piano_led.web.routes.api import create_api_router
from piano_led.web.routes.pages import create_page_router
from piano_led.web.server import create_web_app


def create_fastapi_app(application: Application) -> FastAPI:
    """Build the FastAPI web application bound to a runtime instance."""

    web_root = Path(__file__).resolve().parent
    app = FastAPI(title="Piano LED Learn")
    runtime = application.runtime
    app.mount("/static", StaticFiles(directory=web_root / "static"), name="static")
    app.include_router(create_api_router(application))
    app.include_router(create_page_router(runtime))
    app.mount("/", WSGIMiddleware(create_web_app(runtime, enable_songs_page=False)))
    return app
