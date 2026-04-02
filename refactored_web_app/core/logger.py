from __future__ import annotations

import json
import logging
from datetime import datetime, UTC

from config import APP_LOG_PATH, SERVICE_NAME


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "message": record.getMessage(),
        }
        extra_payload = getattr(record, "payload", None)
        if isinstance(extra_payload, dict):
            payload.update(extra_payload)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def get_logger() -> logging.Logger:
    logger = logging.getLogger(SERVICE_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    APP_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(APP_LOG_PATH, encoding="utf-8")
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(JsonFormatter())
    logger.addHandler(stream_handler)
    logger.propagate = False
    return logger


LOGGER = get_logger()
