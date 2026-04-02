from __future__ import annotations

import sys
from pathlib import Path
from time import perf_counter

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app_5020 import app
from core.service import SERVICE


if __name__ == "__main__":
    started_at = perf_counter()
    SERVICE.health_snapshot(warmup=True)
    elapsed = perf_counter() - started_at
    print(f"5020 warmup completed in {elapsed:.2f}s")
    app.run(host="127.0.0.1", port=5020, debug=False)
