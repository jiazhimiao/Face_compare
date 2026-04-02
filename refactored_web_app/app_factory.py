from __future__ import annotations

import time
from pathlib import Path
from uuid import uuid4

from flask import Flask, g, render_template, request, send_from_directory
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from config import (
    ALLOWED_IMAGE_SUFFIXES,
    AUTH_TOKEN,
    DEFAULT_BLACKLIST_DIR,
    MAX_CONTENT_LENGTH,
    REQUEST_TIMEOUT_SECONDS,
    RUNTIME_DIR,
    RUNTIME_OUTPUT_DIR,
    RUNTIME_UPLOAD_DIR,
    SERVICE_ENV,
    SERVICE_NAME,
    SERVICE_VERSION,
    ensure_default_threshold_config,
    ensure_runtime_dirs,
)
from core.api import error_response, success_response
from core.audit import write_audit_event
from core.errors import AppError, AuthenticationError, RequestTimeoutError, UnsupportedFileError, ValidationError
from core.logger import LOGGER
from core.service import SERVICE
from core.visualization import create_dual_result_visual, create_single_result_visual


ensure_runtime_dirs()
ensure_default_threshold_config()


def create_versioned_app(template_name: str, ui_versions: dict[str, str]) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    def save_upload(file_storage, slot: str) -> Path:
        suffix = Path(file_storage.filename or "").suffix.lower()
        if suffix not in ALLOWED_IMAGE_SUFFIXES:
            raise UnsupportedFileError(file_storage.filename or "")
        target = RUNTIME_UPLOAD_DIR / f"{slot}_{uuid4().hex}{suffix}"
        file_storage.save(target)
        return target

    def require_file(field_name: str):
        file_storage = request.files.get(field_name)
        if file_storage is None or not file_storage.filename:
            raise ValidationError(f"File field `{field_name}` is required", {"field": field_name})
        return file_storage

    def request_summary() -> dict:
        return {
            "request_id": getattr(g, "request_id", ""),
            "path": request.path,
            "method": request.method,
            "remote_addr": request.headers.get("X-Forwarded-For", request.remote_addr),
            "duration_ms": round((time.perf_counter() - getattr(g, "started_at", time.perf_counter())) * 1000, 2),
        }

    def run_with_timeout_budget(operation_name: str, func, *args, **kwargs):
        started_at = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - started_at
        if elapsed > REQUEST_TIMEOUT_SECONDS:
            raise RequestTimeoutError(details={"operation": operation_name, "elapsed_seconds": round(elapsed, 2)})
        return result

    def runtime_url(path: Path) -> str:
        relative = path.resolve().relative_to(RUNTIME_DIR.resolve())
        return f"/runtime/{relative.as_posix()}"

    def runtime_url_or_none(path: Path | None) -> str | None:
        if path is None or not path.exists():
            return None
        try:
            return runtime_url(path)
        except ValueError:
            return None

    @app.before_request
    def before_request() -> None:
        g.request_id = request.headers.get("X-Request-Id", uuid4().hex)
        g.started_at = time.perf_counter()

        if request.path.startswith("/api/") and request.path not in {"/api/v1/health/live", "/api/v1/health/ready"}:
            provided_token = request.headers.get("X-API-Token", "")
            if not AUTH_TOKEN or provided_token != AUTH_TOKEN:
                raise AuthenticationError("Missing or invalid API token")

    @app.after_request
    def after_request(response):
        payload = {
            **request_summary(),
            "status_code": response.status_code,
            "service": SERVICE_NAME,
        }
        LOGGER.info("request_completed", extra={"payload": payload})
        response.headers["X-Request-Id"] = getattr(g, "request_id", "")
        return response

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        LOGGER.warning("app_error", extra={"payload": {**request_summary(), "error_code": error.error_code, "details": error.details}})
        return error_response(error.error_code, error.message, error.http_status, error.details)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_file(error: RequestEntityTooLarge):
        return error_response("FILE_413", "Uploaded file is too large", 413, {"max_bytes": MAX_CONTENT_LENGTH})

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        if isinstance(error, HTTPException):
            return error_response(str(error.code), error.description, error.code or 500)
        LOGGER.exception("unexpected_error", extra={"payload": request_summary()})
        return error_response("SVC_500", "Internal server error", 500)

    @app.get("/")
    def index():
        return render_template(
            template_name,
            service_name=SERVICE_NAME,
            service_version=SERVICE_VERSION,
            service_env=SERVICE_ENV,
            demo_token=AUTH_TOKEN if SERVICE_ENV != "prod" else "",
            ui_versions=ui_versions,
        )

    @app.get("/runtime/<path:filename>")
    def runtime_file(filename: str):
        return send_from_directory(RUNTIME_DIR, filename)

    @app.get("/api/v1/health/live")
    def live_health():
        return success_response(
            {
                "service": SERVICE_NAME,
                "version": SERVICE_VERSION,
                "env": SERVICE_ENV,
                "status": "alive",
            }
        )

    @app.get("/api/v1/health/ready")
    def ready_health():
        snapshot = SERVICE.health_snapshot(warmup=True)
        return success_response({"status": "ready", "snapshot": snapshot})

    @app.get("/api/v1/meta")
    def meta():
        return success_response(
            {
                "service": SERVICE_NAME,
                "version": SERVICE_VERSION,
                "env": SERVICE_ENV,
                "auth_header": "X-API-Token",
                "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
                "routes": [
                    "/api/v1/detect-face",
                    "/api/v1/verify-identity",
                    "/api/v1/check-blacklist",
                    "/api/v1/health/live",
                    "/api/v1/health/ready",
                ],
                "ui_versions": ui_versions,
            }
        )

    @app.post("/api/v1/detect-face")
    def detect_face():
        image_path = save_upload(require_file("image"), "detect")
        result = run_with_timeout_budget("detect_face", SERVICE.detect_face, image_path)
        visual_path = create_single_result_visual(
            "\u4eba\u8138\u68c0\u6d4b\u7ed3\u679c",
            image_path,
            result.bbox,
            [
                f"\u68c0\u6d4b\u7ed3\u679c\uff1a{'\u68c0\u6d4b\u5230\u4eba\u8138' if result.has_face else '\u672a\u68c0\u6d4b\u5230\u4eba\u8138'}",
                f"\u4eba\u8138\u6570\u91cf\uff1a{result.face_count}",
                f"\u8bf4\u660e\uff1a{result.message}",
                "\u5efa\u8bae\u5c06\u6b64\u7ed3\u679c\u4f5c\u4e3a\u540e\u7eed\u8eab\u4efd\u6838\u9a8c\u524d\u7684\u5feb\u901f\u9884\u68c0\u6b65\u9aa4\u3002",
            ],
            RUNTIME_OUTPUT_DIR / f"detect_result_{g.request_id}.png",
        )
        payload = {
            "face_detection": result.to_dict(),
            "image_path": str(image_path),
            "image_url": runtime_url(image_path),
            "visualization_url": runtime_url(visual_path),
        }
        write_audit_event({**request_summary(), "operation": "detect_face", "result": payload["face_detection"]})
        return success_response(payload, result.message)

    @app.post("/api/v1/verify-identity")
    def verify_identity():
        id_card_path = save_upload(require_file("id_card_image"), "id_card")
        face_path = save_upload(require_file("face_image"), "face")
        result = run_with_timeout_budget("verify_identity", SERVICE.verify_identity, id_card_path, face_path)
        visual_path = create_dual_result_visual(
            "\u8eab\u4efd\u6838\u9a8c\u7ed3\u679c",
            id_card_path,
            face_path,
            result.id_card_bbox,
            result.face_bbox,
            [
                f"\u6838\u9a8c\u7ed3\u8bba\uff1a{'\u901a\u8fc7' if result.verified else '\u672a\u901a\u8fc7'}",
                f"\u76f8\u4f3c\u5ea6\uff1a{result.similarity:.4f}",
                f"\u9608\u503c\uff1a{result.threshold:.4f}",
                f"\u8bc1\u4ef6\u7167\u4eba\u8138\u6570\uff1a{result.id_card_face_count}",
                f"\u73b0\u573a\u7167\u4eba\u8138\u6570\uff1a{result.face_image_face_count}",
                f"\u8bf4\u660e\uff1a{result.message}",
            ],
            RUNTIME_OUTPUT_DIR / f"verify_result_{g.request_id}.png",
        )
        payload = {
            "identity_verification": result.to_dict(),
            "id_card_path": str(id_card_path),
            "face_image_path": str(face_path),
            "id_card_url": runtime_url(id_card_path),
            "face_image_url": runtime_url(face_path),
            "visualization_url": runtime_url(visual_path),
        }
        write_audit_event({**request_summary(), "operation": "verify_identity", "result": payload["identity_verification"]})
        return success_response(payload, result.message)

    @app.post("/api/v1/check-blacklist")
    def check_blacklist():
        image_path = save_upload(require_file("image"), "blacklist")
        result = run_with_timeout_budget("check_blacklist", SERVICE.check_blacklist, image_path)
        matched_image_path = DEFAULT_BLACKLIST_DIR / result.matched_name if result.matched_name else image_path
        visual_path = create_dual_result_visual(
            "\u9ed1\u540d\u5355\u6bd4\u5bf9\u7ed3\u679c",
            image_path,
            matched_image_path,
            result.query_bbox,
            None,
            [
                f"\u6bd4\u5bf9\u7ed3\u8bba\uff1a{'\u547d\u4e2d\u9ed1\u540d\u5355' if result.matched else '\u672a\u547d\u4e2d\u9ed1\u540d\u5355'}",
                f"\u547d\u4e2d\u5bf9\u8c61\uff1a{result.matched_name or '\u65e0'}",
                f"\u76f8\u4f3c\u5ea6\uff1a{result.similarity:.4f}",
                f"\u9608\u503c\uff1a{result.threshold:.4f}",
                f"\u8bf4\u660e\uff1a{result.message}",
            ],
            RUNTIME_OUTPUT_DIR / f"blacklist_result_{g.request_id}.png",
        )
        payload = {
            "blacklist_check": result.to_dict(),
            "image_path": str(image_path),
            "image_url": runtime_url(image_path),
            "matched_image_url": runtime_url_or_none(matched_image_path),
            "visualization_url": runtime_url(visual_path),
        }
        write_audit_event({**request_summary(), "operation": "check_blacklist", "result": payload["blacklist_check"]})
        return success_response(payload, result.message)

    @app.post("/api/detect-face")
    def detect_face_legacy():
        return detect_face()

    @app.post("/api/verify-identity")
    def verify_identity_legacy():
        return verify_identity()

    @app.post("/api/check-blacklist")
    def check_blacklist_legacy():
        return check_blacklist()

    return app
