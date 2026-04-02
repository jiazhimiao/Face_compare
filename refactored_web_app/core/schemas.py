from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class FaceFeature:
    image_name: str
    embedding: list[float]
    bbox: list[int]


@dataclass
class FaceDetectionResult:
    has_face: bool
    bbox: list[int] | None
    face_count: int
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IdentityVerificationResult:
    verified: bool
    similarity: float
    threshold: float
    message: str
    id_card_face_count: int = 0
    face_image_face_count: int = 0
    id_card_bbox: list[int] | None = None
    face_bbox: list[int] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BlacklistCheckResult:
    matched: bool
    matched_name: str
    similarity: float
    threshold: float
    message: str
    face_count: int = 0
    query_bbox: list[int] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProcessedUserResult:
    user_id: str
    face_detection: dict[str, Any]
    identity_verification: dict[str, Any]
    blacklist_check: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
