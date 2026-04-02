from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app_5009 import app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5009, debug=False)
