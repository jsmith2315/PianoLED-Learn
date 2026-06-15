"""Module entrypoint for ``python -m piano_led`` from the repo root."""

import sys

from piano_led.main import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
