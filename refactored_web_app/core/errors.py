from __future__ import annotations


class AppError(Exception):
    def __init__(self, error_code: str, message: str, http_status: int = 400, details: dict | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.http_status = http_status
        self.details = details or {}


class AuthenticationError(AppError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__("AUTH_401", message, http_status=401)


class ValidationError(AppError):
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__("REQ_400", message, http_status=400, details=details)


class UnsupportedFileError(AppError):
    def __init__(self, filename: str) -> None:
        super().__init__("FILE_415", f"Unsupported image type: {filename}", http_status=415)


class FaceNotFoundError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("FACE_404", message, http_status=422)


class ServiceUnavailableError(AppError):
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__("SVC_503", message, http_status=503, details=details)


class RequestTimeoutError(AppError):
    def __init__(self, message: str = "Algorithm processing exceeded timeout budget", details: dict | None = None) -> None:
        super().__init__("SVC_504", message, http_status=504, details=details)
