from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock

import cv2
from insightface.app import FaceAnalysis

from config import DET_THRESH, DEVICE_ID, INPUT_SIZE, MODEL_NAME, MODEL_ROOT


@dataclass
class ExtractedFace:
    embedding: list[float]
    bbox: list[int]
    face_count: int


class FaceEngine:
    def __init__(self) -> None:
        self._app: FaceAnalysis | None = None
        self._lock = Lock()

    def initialize(self) -> FaceAnalysis:
        if self._app is not None:
            return self._app

        with self._lock:
            if self._app is None:
                app = FaceAnalysis(name=MODEL_NAME, root=MODEL_ROOT)
                app.prepare(ctx_id=DEVICE_ID, det_thresh=DET_THRESH, det_size=INPUT_SIZE)
                self._app = app
        return self._app

    def read_image(self, image_path: str | Path):
        return cv2.imread(str(image_path))

    def extract(self, image_path: str | Path) -> ExtractedFace | None:
        image = self.read_image(image_path)
        if image is None:
            return None

        app = self.initialize()
        faces = app.get(image)
        if not faces:
            return None

        face = max(
            faces,
            key=lambda item: (item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1]),
        )
        return ExtractedFace(
            embedding=face.normed_embedding.astype(float).tolist(),
            bbox=face.bbox.astype(int).tolist(),
            face_count=len(faces),
        )

    def health_status(self) -> dict[str, object]:
        return {
            "initialized": self._app is not None,
            "model_name": MODEL_NAME,
            "device_id": DEVICE_ID,
            "input_size": INPUT_SIZE,
        }


ENGINE = FaceEngine()
