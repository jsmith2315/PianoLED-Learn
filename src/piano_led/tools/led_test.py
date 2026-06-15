from __future__ import annotations

from piano_led.app import build_application


def run_once() -> str:
    application = build_application()
    application.runtime.handle_chase_step()
    return application.runtime.describe()

