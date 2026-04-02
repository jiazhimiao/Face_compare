from __future__ import annotations

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = BASE_DIR / "runtime"
RUNTIME_FEATURE_DIR = RUNTIME_DIR / "features"
RUNTIME_OUTPUT_DIR = RUNTIME_DIR / "output"
RUNTIME_UPLOAD_DIR = RUNTIME_DIR / "uploads"
RUNTIME_LOG_DIR = RUNTIME_DIR / "logs"
RUNTIME_AUDIT_DIR = RUNTIME_DIR / "audit"
RUNTIME_CONFIG_DIR = RUNTIME_DIR / "config"

ORIGINAL_BASE_DIR = BASE_DIR.parent
DEFAULT_PHOTOS_DIR = ORIGINAL_BASE_DIR / "photos"
DEFAULT_BLACKLIST_DIR = ORIGINAL_BASE_DIR / "blacklist"
DEFAULT_ALL_PHOTO_DIR = ORIGINAL_BASE_DIR / "all_photo"
DEFAULT_SAME_PERSON_DIR = ORIGINAL_BASE_DIR / "same_person"
DEFAULT_DIFFERENT_PERSON_DIR = ORIGINAL_BASE_DIR / "different_person"

SERVICE_NAME = os.getenv("FACE_COMPARE_SERVICE_NAME", "face-compare-python-service")
SERVICE_VERSION = os.getenv("FACE_COMPARE_SERVICE_VERSION", "1.0.0")
SERVICE_ENV = os.getenv("FACE_COMPARE_SERVICE_ENV", "dev")

MODEL_NAME = os.getenv("FACE_COMPARE_MODEL_NAME", "buffalo_l")
MODEL_ROOT = os.getenv("FACE_COMPARE_MODEL_ROOT", "~/.insightface")
DEVICE_ID = int(os.getenv("FACE_COMPARE_DEVICE_ID", "-1"))
DET_THRESH = float(os.getenv("FACE_COMPARE_DET_THRESH", "0.5"))
INPUT_SIZE = (
    int(os.getenv("FACE_COMPARE_INPUT_WIDTH", "640")),
    int(os.getenv("FACE_COMPARE_INPUT_HEIGHT", "640")),
)

IDENTITY_THRESHOLD = float(os.getenv("FACE_COMPARE_IDENTITY_THRESHOLD", "0.60"))
BLACKLIST_THRESHOLD = float(os.getenv("FACE_COMPARE_BLACKLIST_THRESHOLD", "0.65"))

ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}
MAX_CONTENT_LENGTH = int(os.getenv("FACE_COMPARE_MAX_CONTENT_LENGTH", str(10 * 1024 * 1024)))
RANDOM_SEED = int(os.getenv("FACE_COMPARE_RANDOM_SEED", "42"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("FACE_COMPARE_REQUEST_TIMEOUT_SECONDS", "30"))
AUTH_TOKEN = os.getenv("FACE_COMPARE_AUTH_TOKEN", "change-me")

APP_HOST = os.getenv("FACE_COMPARE_APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("FACE_COMPARE_APP_PORT", "5000"))
APP_DEBUG = os.getenv("FACE_COMPARE_APP_DEBUG", "false").lower() == "true"

THRESHOLD_CONFIG_PATH = RUNTIME_CONFIG_DIR / "thresholds.json"
APP_LOG_PATH = RUNTIME_LOG_DIR / "application.log"
AUDIT_LOG_PATH = RUNTIME_AUDIT_DIR / "audit.jsonl"


def ensure_runtime_dirs() -> None:
    for path in (
        RUNTIME_DIR,
        RUNTIME_FEATURE_DIR,
        RUNTIME_OUTPUT_DIR,
        RUNTIME_UPLOAD_DIR,
        RUNTIME_LOG_DIR,
        RUNTIME_AUDIT_DIR,
        RUNTIME_CONFIG_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def ensure_default_threshold_config() -> None:
    ensure_runtime_dirs()
    if THRESHOLD_CONFIG_PATH.exists():
        return

    payload = {
        "identity_threshold": IDENTITY_THRESHOLD,
        "blacklist_threshold": BLACKLIST_THRESHOLD,
        "source": "env_or_default",
        "notes": "Override this file during deployment if ROC-calibrated thresholds are required.",
    }
    THRESHOLD_CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_thresholds() -> dict[str, float]:
    ensure_default_threshold_config()
    payload = json.loads(THRESHOLD_CONFIG_PATH.read_text(encoding="utf-8"))
    return {
        "identity_threshold": float(payload.get("identity_threshold", IDENTITY_THRESHOLD)),
        "blacklist_threshold": float(payload.get("blacklist_threshold", BLACKLIST_THRESHOLD)),
    }
