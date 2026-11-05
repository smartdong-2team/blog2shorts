
import requests
from fastapi import APIRouter, HTTPException

from app.schemas.content import (
    ContentExtractRequest,
    ContentExtractResponse,
    SourceInfo,
    ImageAsset,
)
from app.services.content_extractor import (
    extract_content,
    UnsupportedUrlError,
    ExtractionError,
)
from app.services.storage import (
    save_image,
    ImageStorageError,
)

router = APIRouter(prefix="/content", tags=["Content"])


@router.post("/extract", response_model=ContentExtractResponse)
def extract_blog_content(request: ContentExtractRequest):
    # 1. 블로그 콘텐츠 추출
    try:
        content = extract_content(str(request.url))
    except UnsupportedUrlError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "UNSUPPORTED_URL", "message": str(exc)},
        ) from exc
    except ExtractionError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "EXTRACTION_FAILED", "message": str(exc)},
        ) from exc

    # 2. 이미지 다운로드 및 저장
    images = []

    for image_url in content.image_urls:
        try:
            asset = save_image(image_url)
        except (ImageStorageError, requests.RequestException):
            # 이미지 저장 실패는 전체 추출 실패로 처리하지 않음
            continue

        images.append(
            ImageAsset(
                asset_id=str(asset.asset_id),
                url=asset.url,
                width=asset.width,
                height=asset.height,
                alt=None,
            )
        )

    # 3. 최종 API 응답 구성
    return ContentExtractResponse(
        source=SourceInfo(
            platform="naver_blog",
            blog_id=content.blog_id,
            log_no=content.log_no,
            url=content.url,
        ),
        title=content.title,
        text=content.text,
        images=images,
    )
