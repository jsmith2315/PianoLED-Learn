from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StateStore:
    data: dict = field(default_factory=dict)

    def update(self, **changes) -> None:
        self.data.update(changes)

    def snapshot(self) -> dict:
        return dict(self.data)

