
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.services.content_extractor import (
    ExtractedContent,
    UnsupportedUrlError,
    ExtractionError,
)
from app.services.storage import (
    StoredAsset,
    ImageStorageError,
)


client = TestClient(app)

TEST_URL = "https://blog.naver.com/copper567/224442374562"


def mock_content():
    """테스트에서 사용할 가짜 블로그 추출 결과"""
    return ExtractedContent(
        blog_id="copper567",
        log_no="224442374562",
        url=TEST_URL,
        title="자동차정비기능사 공부방법",
        text="자동차 정비의 기본 원리를 공부해보세요.\n[이미지 1]\n두 번째 문단\n[이미지 2]",
        image_urls=[
            "https://mblogthumb-phinf.pstatic.net/test1.jpg",
            "https://mblogthumb-phinf.pstatic.net/test2.jpg",
        ],
    )


def mock_asset():
    """테스트에서 사용할 가짜 이미지 저장 결과"""
    asset_id = UUID("d2c8f7b3-41d5-42ad-a250-599058ef0571")

    return StoredAsset(
        asset_id=asset_id,
        path=Path("/tmp/test.jpg"),
        media_type="image/jpeg",
        width=800,
        height=600,
    )


# 1. 정상적인 블로그 URL
def test_extract_content_success():
    with (
        patch(
            "app.api.v1.content.extract_content",
            return_value=mock_content(),
        ),
        patch(
            "app.api.v1.content.save_image",
            return_value=mock_asset(),
        ),
    ):
        response = client.post(
            "/api/v1/content/extract",
            json={"url": TEST_URL},
        )

    assert response.status_code == 200

    data = response.json()

    assert data["source"]["platform"] == "naver_blog"
    assert data["source"]["blog_id"] == "copper567"
    assert data["title"] == "자동차정비기능사 공부방법"
    assert "자동차 정비" in data["text"]

    assert len(data["images"]) == 2
    assert data["images"][0]["width"] == 800
    assert data["images"][0]["height"] == 600


# 2. 지원하지 않는 URL
def test_extract_unsupported_url():
    with patch(
        "app.api.v1.content.extract_content",
        side_effect=UnsupportedUrlError(
            "네이버 블로그 URL만 지원합니다."
        ),
    ):
        response = client.post(
            "/api/v1/content/extract",
            json={"url": "https://example.com/post/123"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_URL"


# 3. 블로그 콘텐츠 추출 실패
def test_extract_content_failure():
    with patch(
        "app.api.v1.content.extract_content",
        side_effect=ExtractionError(
            "블로그 본문을 찾을 수 없습니다."
        ),
    ):
        response = client.post(
            "/api/v1/content/extract",
            json={"url": TEST_URL},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EXTRACTION_FAILED"


# 4. 일부 이미지 다운로드 실패
def test_extract_partial_image_failure():
    def fake_save_image(url):
        if "test2.jpg" in url:
            raise ImageStorageError("이미지 다운로드 실패")

        return mock_asset()

    with (
        patch(
            "app.api.v1.content.extract_content",
            return_value=mock_content(),
        ),
        patch(
            "app.api.v1.content.save_image",
            side_effect=fake_save_image,
        ),
    ):
        response = client.post(
            "/api/v1/content/extract",
            json={"url": TEST_URL},
        )

    assert response.status_code == 200

    data = response.json()

    assert len(data["images"]) == 1
    assert data["images"][0]["asset_id"] == (
        "d2c8f7b3-41d5-42ad-a250-599058ef0571"
    )


# 5. 저장에 실패한 이미지 자리는 본문에서 빠지고, 남은 이미지 번호가 응답 순서에 맞춰진다
def test_extract_renumbers_image_markers():
    def fake_save_image(url):
        if "test1.jpg" in url:
            raise ImageStorageError("이미지 다운로드 실패")

        return mock_asset()

    with (
        patch(
            "app.api.v1.content.extract_content",
            return_value=mock_content(),
        ),
        patch(
            "app.api.v1.content.save_image",
            side_effect=fake_save_image,
        ),
    ):
        response = client.post(
            "/api/v1/content/extract",
            json={"url": TEST_URL},
        )

    data = response.json()
    assert len(data["images"]) == 1
    assert "[이미지 2]" not in data["text"]
    assert data["text"] == "자동차 정비의 기본 원리를 공부해보세요.\n두 번째 문단\n[이미지 1]"


# 6. 추출기는 <img> 자리에 "[이미지 N]"을 넣어 글과 이미지 순서를 남긴다
def test_extractor_marks_image_positions():
    from bs4 import BeautifulSoup

    from app.services import content_extractor

    html = """
    <div class="se-main-container">
      <p>첫 문단</p>
      <img src="https://img.example.com/a.jpg">
      <p>둘째 문단</p>
      <img data-src="https://img.example.com/b.jpg">
      <img src="https://img.example.com/a.jpg">
      <img src="http://img.example.com/insecure.jpg">
    </div>
    """

    with patch.object(
        content_extractor,
        "fetch_html",
        return_value=BeautifulSoup(html, "html.parser"),
    ):
        result = content_extractor.extract_content(TEST_URL)

    assert result.image_urls == [
        "https://img.example.com/a.jpg",
        "https://img.example.com/b.jpg",
    ]
    assert result.text == "첫 문단\n[이미지 1]\n둘째 문단\n[이미지 2]\n[이미지 1]"
