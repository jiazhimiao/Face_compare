from __future__ import annotations

import io
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app
from config import AUTH_TOKEN


def assert_png_exists(payload: dict, key: str) -> None:
    url = payload["data"].get(key)
    assert url, f"missing url for {key}"
    relative = url.removeprefix("/runtime/")
    target = ROOT_DIR / "runtime" / relative
    assert target.exists(), f"generated asset not found: {target}"


def run() -> None:
    client = app.test_client()
    photos_dir = ROOT_DIR.parent / "photos"
    blacklist_dir = ROOT_DIR.parent / "blacklist"

    id_card = photos_dir / "34944_card_front.jpeg"
    face = photos_dir / "34944_face_photo_list.jpeg"
    blacklist_face = blacklist_dir / "34944_face_photo_list.jpeg"
    headers = {"X-API-Token": AUTH_TOKEN, "X-Request-Id": "smoke-test-default"}

    home = client.get("/")
    assert home.status_code == 200
    home_html = home.data.decode("utf-8")
    assert "智能人脸核验平台" in home_html
    for marker in ("Face Compare Ops", "冻结版 5014", "版本定位", "验证清单", "实时摘要", "布局原则"):
        assert marker not in home_html

    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    print("health_live", response.status_code, json.dumps(response.get_json(), ensure_ascii=False))

    with face.open("rb") as file:
        response = client.post(
            "/api/v1/detect-face",
            headers=headers,
            data={"image": (io.BytesIO(file.read()), face.name)},
            content_type="multipart/form-data",
        )
    detect_payload = response.get_json()
    assert response.status_code == 200
    assert detect_payload["success"] is True
    assert_png_exists(detect_payload, "visualization_url")
    print("detect_face", response.status_code, json.dumps(detect_payload, ensure_ascii=False))

    with id_card.open("rb") as id_file, face.open("rb") as face_file:
        response = client.post(
            "/api/v1/verify-identity",
            headers=headers,
            data={
                "id_card_image": (io.BytesIO(id_file.read()), id_card.name),
                "face_image": (io.BytesIO(face_file.read()), face.name),
            },
            content_type="multipart/form-data",
        )
    verify_payload = response.get_json()
    assert response.status_code == 200
    assert verify_payload["success"] is True
    assert_png_exists(verify_payload, "visualization_url")
    print("verify_identity", response.status_code, json.dumps(verify_payload, ensure_ascii=False))

    with blacklist_face.open("rb") as file:
        response = client.post(
            "/api/v1/check-blacklist",
            headers=headers,
            data={"image": (io.BytesIO(file.read()), blacklist_face.name)},
            content_type="multipart/form-data",
        )
    blacklist_payload = response.get_json()
    assert response.status_code == 200
    assert blacklist_payload["success"] is True
    assert_png_exists(blacklist_payload, "visualization_url")
    print("check_blacklist", response.status_code, json.dumps(blacklist_payload, ensure_ascii=False))


if __name__ == "__main__":
    run()
