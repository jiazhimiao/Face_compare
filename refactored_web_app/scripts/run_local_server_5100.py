from __future__ import annotations

import sys
from pathlib import Path
from time import perf_counter

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app_5100 import app
from core.service import SERVICE

HOST = "127.0.0.1"
PORT = 5100


if __name__ == "__main__":
    started_at = perf_counter()
    SERVICE.health_snapshot(warmup=True)
    elapsed = perf_counter() - started_at
    print(f"[5100] warmup completed in {elapsed:.2f}s", flush=True)
    print("[5100] Face Compare Platform is starting", flush=True)
    print(f"[5100] URL: http://{HOST}:{PORT}", flush=True)
    print("[5100] Press Ctrl+C to stop", flush=True)
    app.run(host=HOST, port=PORT, debug=False)
