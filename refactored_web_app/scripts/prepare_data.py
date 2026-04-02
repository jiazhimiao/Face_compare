from __future__ import annotations

import random
import shutil
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import DEFAULT_ALL_PHOTO_DIR, RANDOM_SEED


def prepare_same_person_data(source_dir: Path, target_dir: Path, limit: int = 1000) -> int:
    target_dir.mkdir(parents=True, exist_ok=True)

    card_front_files: dict[str, Path] = {}
    face_photo_files: dict[str, Path] = {}

    for file_path in source_dir.iterdir():
        if file_path.name.endswith("_card_front.jpeg"):
            card_front_files[file_path.stem.replace("_card_front", "")] = file_path
        elif file_path.name.endswith("_face_photo_list.jpeg"):
            face_photo_files[file_path.stem.replace("_face_photo_list", "")] = file_path

    matched_users = sorted(set(card_front_files) & set(face_photo_files))[:limit]
    for user_id in matched_users:
        shutil.copy2(card_front_files[user_id], target_dir / f"{user_id}_card_front.jpeg")
        shutil.copy2(face_photo_files[user_id], target_dir / f"{user_id}_face_photo_list.jpeg")
    return len(matched_users)


def prepare_different_person_data(source_dir: Path, target_dir: Path, limit: int = 2000) -> int:
    target_dir.mkdir(parents=True, exist_ok=True)

    face_files = [path for path in source_dir.iterdir() if path.name.endswith("_face_photo_list.jpeg")]
    random.Random(RANDOM_SEED).shuffle(face_files)
    selected = face_files[:limit]

    for file_path in selected:
        shutil.copy2(file_path, target_dir / file_path.name)
    return len(selected)


if __name__ == "__main__":
    runtime_dir = Path(__file__).resolve().parents[1] / "runtime"
    same_count = prepare_same_person_data(DEFAULT_ALL_PHOTO_DIR, runtime_dir / "same_person")
    different_count = prepare_different_person_data(DEFAULT_ALL_PHOTO_DIR, runtime_dir / "different_person")
    print({"same_person_pairs": same_count, "different_person_images": different_count})
