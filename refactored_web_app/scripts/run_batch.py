from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import DEFAULT_PHOTOS_DIR, RUNTIME_OUTPUT_DIR, ensure_runtime_dirs
from core.service import SERVICE
from core.visualization import create_text_summary


def main() -> None:
    ensure_runtime_dirs()
    results = SERVICE.batch_process(DEFAULT_PHOTOS_DIR)

    output_path = RUNTIME_OUTPUT_DIR / "batch_results.json"
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_lines = [
        f"Processed users: {len(results)}",
        f"Verified count: {sum(1 for item in results if item['identity_verification']['verified'])}",
        f"Blacklist hits: {sum(1 for item in results if item['blacklist_check']['matched'])}",
    ]
    create_text_summary("Batch Summary", summary_lines, RUNTIME_OUTPUT_DIR / "batch_summary.jpg")
    print(f"Batch results saved to {output_path}")


if __name__ == "__main__":
    main()
