from __future__ import annotations

import json
import pickle
from pathlib import Path

from config import ALLOWED_IMAGE_SUFFIXES
from core.model import ENGINE
from core.schemas import FaceFeature


def list_image_paths(image_dir: str | Path) -> list[Path]:
    image_dir = Path(image_dir)
    if not image_dir.exists():
        return []
    return sorted(
        path
        for path in image_dir.iterdir()
        if path.is_file() and path.suffix.lower() in ALLOWED_IMAGE_SUFFIXES
    )


def collect_file_state(image_paths: list[Path]) -> dict[str, dict[str, float | int]]:
    state: dict[str, dict[str, float | int]] = {}
    for path in image_paths:
        stat = path.stat()
        state[path.name] = {"size": stat.st_size, "mtime": stat.st_mtime}
    return state


def load_feature_cache(cache_path: str | Path) -> dict:
    cache_path = Path(cache_path)
    if not cache_path.exists():
        return {"file_state": {}, "features": {}}
    with cache_path.open("rb") as file:
        return pickle.load(file)


def save_feature_cache(cache_path: str | Path, payload: dict) -> None:
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("wb") as file:
        pickle.dump(payload, file)

    metadata_path = cache_path.with_suffix(".meta.json")
    metadata = {
        "feature_count": len(payload.get("features", {})),
        "tracked_files": sorted(payload.get("file_state", {}).keys()),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")


def build_features(image_dir: str | Path) -> dict[str, FaceFeature]:
    result: dict[str, FaceFeature] = {}
    for image_path in list_image_paths(image_dir):
        extracted = ENGINE.extract(image_path)
        if extracted is None:
            continue
        result[image_path.name] = FaceFeature(
            image_name=image_path.name,
            embedding=extracted.embedding,
            bbox=extracted.bbox,
        )
    return result


def get_or_update_features(image_dir: str | Path, cache_path: str | Path, force_update: bool = False) -> dict[str, FaceFeature]:
    image_paths = list_image_paths(image_dir)
    current_state = collect_file_state(image_paths)
    cached_payload = load_feature_cache(cache_path)
    cached_state = cached_payload.get("file_state", {})

    if force_update or cached_state != current_state:
        features = build_features(image_dir)
        payload = {
            "file_state": current_state,
            "features": {name: feature.__dict__ for name, feature in features.items()},
        }
        save_feature_cache(cache_path, payload)
        return features

    restored: dict[str, FaceFeature] = {}
    for name, raw_feature in cached_payload.get("features", {}).items():
        restored[name] = FaceFeature(**raw_feature)
    return restored
