from __future__ import annotations


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    cleaned = value.lstrip("#")
    if len(cleaned) != 6:
        raise ValueError(f"Expected 6 hex digits, got {value!r}")
    return tuple(int(cleaned[index : index + 2], 16) for index in range(0, 6, 2))

