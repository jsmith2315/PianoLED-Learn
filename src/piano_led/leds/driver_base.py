from __future__ import annotations

from abc import ABC, abstractmethod


class LedDriver(ABC):
    @abstractmethod
    def set_pixel(self, index: int, color: tuple[int, int, int]) -> None:
        raise NotImplementedError

    @abstractmethod
    def show(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError

