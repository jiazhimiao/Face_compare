from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app_5006 import app


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5006, debug=False)
