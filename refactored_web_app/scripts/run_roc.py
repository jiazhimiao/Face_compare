from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import auc, roc_curve

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import DEFAULT_DIFFERENT_PERSON_DIR, DEFAULT_SAME_PERSON_DIR, RANDOM_SEED, ensure_runtime_dirs
from core.model import ENGINE


def gather_same_pairs(folder: Path) -> list[tuple[float, int]]:
    grouped: dict[str, dict[str, Path]] = {}
    for path in folder.iterdir():
        if not path.is_file():
            continue
        if path.name.endswith("_card_front.jpeg"):
            user_id = path.name.replace("_card_front.jpeg", "")
            grouped.setdefault(user_id, {})["card"] = path
        elif path.name.endswith("_face_photo_list.jpeg"):
            user_id = path.name.replace("_face_photo_list.jpeg", "")
            grouped.setdefault(user_id, {})["face"] = path

    pairs: list[tuple[float, int]] = []
    for items in grouped.values():
        if "card" not in items or "face" not in items:
            continue
        card = ENGINE.extract(items["card"])
        face = ENGINE.extract(items["face"])
        if card is None or face is None:
            continue
        similarity = float(np.dot(np.array(card.embedding), np.array(face.embedding)))
        pairs.append((similarity, 1))
    return pairs


def gather_different_pairs(folder: Path, sample_pairs: int = 200) -> list[tuple[float, int]]:
    all_files = [path for path in folder.iterdir() if path.is_file()]
    randomizer = random.Random(RANDOM_SEED)
    randomizer.shuffle(all_files)

    pairs: list[tuple[float, int]] = []
    used = 0
    for index in range(0, len(all_files) - 1, 2):
        if used >= sample_pairs:
            break
        face_a = ENGINE.extract(all_files[index])
        face_b = ENGINE.extract(all_files[index + 1])
        if face_a is None or face_b is None:
            continue
        similarity = float(np.dot(np.array(face_a.embedding), np.array(face_b.embedding)))
        pairs.append((similarity, 0))
        used += 1
    return pairs


def main() -> None:
    ensure_runtime_dirs()
    same_pairs = gather_same_pairs(DEFAULT_SAME_PERSON_DIR)
    different_pairs = gather_different_pairs(DEFAULT_DIFFERENT_PERSON_DIR)

    all_pairs = same_pairs + different_pairs
    labels = np.array([label for _, label in all_pairs])
    scores = np.array([score for score, _ in all_pairs])

    fpr, tpr, thresholds = roc_curve(labels, scores)
    auc_score = auc(fpr, tpr)

    result = {
        "auc": float(auc_score),
        "pair_count": len(all_pairs),
        "same_pair_count": len(same_pairs),
        "different_pair_count": len(different_pairs),
        "thresholds": [
            {"threshold": float(threshold), "tpr": float(tpr_item), "fpr": float(fpr_item)}
            for threshold, tpr_item, fpr_item in zip(thresholds, tpr, fpr)
        ],
    }

    output_path = Path(__file__).resolve().parents[1] / "runtime" / "output" / "roc_summary.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ROC summary saved to {output_path}")


if __name__ == "__main__":
    main()
