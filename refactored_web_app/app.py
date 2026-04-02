from __future__ import annotations

from app_5100 import app
from config import APP_DEBUG, APP_HOST, APP_PORT


if __name__ == "__main__":
    app.run(host=APP_HOST, port=APP_PORT, debug=APP_DEBUG)
