"""Abstract LED driver interface shared by fake and Pi backends."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LedDriver(ABC):
    """Minimal LED strip interface required by the runtime."""
    @abstractmethod
    def set_pixel(self, index: int, color: tuple[int, int, int]) -> None:
        raise NotImplementedError

    @abstractmethod
    def show(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError

    def set_brightness(self, brightness: int) -> None:
        """Apply a strip brightness level when the backend supports it."""

        return None
