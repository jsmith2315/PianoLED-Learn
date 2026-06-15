"""Tiny helper for one-off LED smoke testing."""

from __future__ import annotations

from piano_led.app import build_application


def run_once() -> str:
    """Run a single chase step and return the runtime summary."""

    application = build_application()
    application.runtime.handle_chase_step()
    return application.runtime.describe()
