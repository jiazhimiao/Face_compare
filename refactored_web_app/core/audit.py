from __future__ import annotations

import json
from datetime import datetime, UTC

from config import AUDIT_LOG_PATH


def write_audit_event(payload: dict) -> None:
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        **payload,
    }
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
