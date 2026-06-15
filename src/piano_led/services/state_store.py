"""Small state container for UI-readable runtime snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StateStore:
    """Mutable store for current runtime state exposed to the UI layer."""
    data: dict = field(default_factory=dict)

    def update(self, **changes) -> None:
        self.data.update(changes)

    def snapshot(self) -> dict:
        return dict(self.data)
