from __future__ import annotations

from flask import jsonify, g


def success_response(data: dict, message: str = "OK", status_code: int = 200):
    return (
        jsonify(
            {
                "success": True,
                "request_id": getattr(g, "request_id", ""),
                "message": message,
                "error_code": None,
                "data": data,
            }
        ),
        status_code,
    )


def error_response(error_code: str, message: str, status_code: int, details: dict | None = None):
    return (
        jsonify(
            {
                "success": False,
                "request_id": getattr(g, "request_id", ""),
                "message": message,
                "error_code": error_code,
                "data": {},
                "details": details or {},
            }
        ),
        status_code,
    )
