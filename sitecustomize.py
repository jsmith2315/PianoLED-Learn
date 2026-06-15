from __future__ import annotations

import sys
from pathlib import Path


SRC_PATH = Path(__file__).resolve().parent / "src"
if SRC_PATH.is_dir():
    src = str(SRC_PATH)
    if src not in sys.path:
        sys.path.insert(0, src)

