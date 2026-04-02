from __future__ import annotations

from pathlib import Path

import numpy as np

from config import DEFAULT_BLACKLIST_DIR, RUNTIME_FEATURE_DIR, load_thresholds
from core.errors import AppError, FaceNotFoundError, ServiceUnavailableError
from core.features import get_or_update_features
from core.model import ENGINE
from core.schemas import (
    BlacklistCheckResult,
    FaceDetectionResult,
    IdentityVerificationResult,
    ProcessedUserResult,
)


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    return float(np.dot(np.array(vector_a), np.array(vector_b)))


class FaceCompareService:
    def __init__(self) -> None:
        self.blacklist_dir = DEFAULT_BLACKLIST_DIR
        self.blacklist_cache_path = RUNTIME_FEATURE_DIR / "blacklist_features.pkl"

    @property
    def thresholds(self) -> dict[str, float]:
        return load_thresholds()

    def detect_face(self, image_path: str | Path) -> FaceDetectionResult:
        extracted = ENGINE.extract(image_path)
        if extracted is None:
            return FaceDetectionResult(False, None, 0, "未检测到人脸")
        return FaceDetectionResult(True, extracted.bbox, extracted.face_count, "检测到人脸")

    def verify_identity(
        self,
        id_card_image_path: str | Path,
        face_image_path: str | Path,
        threshold: float | None = None,
    ) -> IdentityVerificationResult:
        threshold = self.thresholds["identity_threshold"] if threshold is None else threshold
        id_face = ENGINE.extract(id_card_image_path)
        if id_face is None:
            raise FaceNotFoundError("证件照中未检测到人脸")

        live_face = ENGINE.extract(face_image_path)
        if live_face is None:
            raise FaceNotFoundError("现场照中未检测到人脸")

        similarity = cosine_similarity(id_face.embedding, live_face.embedding)
        verified = similarity >= threshold
        message = "身份核验通过" if verified else "身份核验未通过"
        return IdentityVerificationResult(
            verified=verified,
            similarity=similarity,
            threshold=threshold,
            message=message,
            id_card_face_count=id_face.face_count,
            face_image_face_count=live_face.face_count,
            id_card_bbox=id_face.bbox,
            face_bbox=live_face.bbox,
        )

    def check_blacklist(
        self,
        face_image_path: str | Path,
        threshold: float | None = None,
    ) -> BlacklistCheckResult:
        threshold = self.thresholds["blacklist_threshold"] if threshold is None else threshold
        query_face = ENGINE.extract(face_image_path)
        if query_face is None:
            raise FaceNotFoundError("待检测图片中未检测到人脸")

        blacklist_features = get_or_update_features(self.blacklist_dir, self.blacklist_cache_path)
        if not blacklist_features:
            raise ServiceUnavailableError("黑名单特征库不可用")

        max_similarity = -1.0
        matched_name = ""
        for name, feature in blacklist_features.items():
            similarity = cosine_similarity(query_face.embedding, feature.embedding)
            if similarity > max_similarity:
                max_similarity = similarity
                matched_name = name

        matched = max_similarity >= threshold
        message = "命中黑名单" if matched else "未命中黑名单"
        return BlacklistCheckResult(
            matched=matched,
            matched_name=matched_name,
            similarity=max_similarity,
            threshold=threshold,
            message=message,
            face_count=query_face.face_count,
            query_bbox=query_face.bbox,
        )

    def process_user(self, user_id: str, id_card_path: str | Path, face_path: str | Path) -> ProcessedUserResult:
        face_detection = {
            "id_card": self.detect_face(id_card_path).to_dict(),
            "face_photo": self.detect_face(face_path).to_dict(),
        }
        try:
            identity = self.verify_identity(id_card_path, face_path).to_dict()
        except AppError as error:
            identity = {
                "verified": False,
                "similarity": 0.0,
                "threshold": self.thresholds["identity_threshold"],
                "message": error.message,
                "error_code": error.error_code,
            }

        try:
            blacklist = self.check_blacklist(face_path).to_dict()
        except AppError as error:
            blacklist = {
                "matched": False,
                "matched_name": "",
                "similarity": 0.0,
                "threshold": self.thresholds["blacklist_threshold"],
                "message": error.message,
                "error_code": error.error_code,
            }
        return ProcessedUserResult(user_id, face_detection, identity, blacklist)

    def scan_user_pairs(self, base_folder: str | Path) -> list[tuple[str, Path, Path]]:
        base_folder = Path(base_folder)
        card_files: dict[str, Path] = {}
        face_files: dict[str, Path] = {}

        for image_path in base_folder.iterdir():
            if not image_path.is_file():
                continue
            name = image_path.name
            if name.endswith("_card_front.jpeg"):
                card_files[name.replace("_card_front.jpeg", "")] = image_path
            elif name.endswith("_face_photo_list.jpeg"):
                face_files[name.replace("_face_photo_list.jpeg", "")] = image_path

        users = sorted(set(card_files) & set(face_files))
        return [(user_id, card_files[user_id], face_files[user_id]) for user_id in users]

    def batch_process(self, base_folder: str | Path) -> list[dict]:
        return [self.process_user(user_id, id_card, face).to_dict() for user_id, id_card, face in self.scan_user_pairs(base_folder)]

    def health_snapshot(self, warmup: bool = False) -> dict[str, object]:
        if warmup:
            ENGINE.initialize()
        return {
            "engine": ENGINE.health_status(),
            "thresholds": self.thresholds,
            "blacklist_dir_exists": self.blacklist_dir.exists(),
            "blacklist_cache_path": str(self.blacklist_cache_path),
        }


SERVICE = FaceCompareService()
