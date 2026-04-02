from __future__ import annotations

from app_factory import create_versioned_app


app = create_versioned_app(
    "index_keep_5014.html",
    {
        "current_port_5014": "http://127.0.0.1:5014",
        "stable_port_5009": "http://127.0.0.1:5009",
        "current_port_5006": "http://127.0.0.1:5006",
    },
)
