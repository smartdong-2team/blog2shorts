
from pathlib import Path
from uuid import UUID
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.storage import StoredAsset


client = TestClient(app)

TEST_ASSET_ID = UUID("d2c8f7b3-41d5-42ad-a250-599058ef0571")


# 1. 존재하는 이미지 조회
def test_get_asset_success(tmp_path: Path):
    # 테스트용 이미지 파일 생성
    image_bytes = b"fake-image-content"
    image_path = tmp_path / "test.jpg"
    image_path.write_bytes(image_bytes)

    # Storage가 반환할 가짜 이미지 정보
    mock_asset = StoredAsset(
        asset_id=TEST_ASSET_ID,
        path=image_path,
        media_type="image/jpeg",
        width=800,
        height=600,
    )

    with patch(
        "app.api.v1.assets.get_asset",
        return_value=mock_asset,
    ):
        response = client.get(
            f"/api/v1/assets/{TEST_ASSET_ID}"
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == image_bytes


# 2. 존재하지 않는 이미지 조회
def test_get_asset_not_found():
    with patch(
        "app.api.v1.assets.get_asset",
        return_value=None,
    ):
        response = client.get(
            f"/api/v1/assets/{TEST_ASSET_ID}"
        )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "NOT_FOUND"


# 3. 잘못된 UUID 형식
def test_get_asset_invalid_uuid():
    response = client.get(
        "/api/v1/assets/not-a-valid-uuid"
    )

    assert response.status_code == 422
