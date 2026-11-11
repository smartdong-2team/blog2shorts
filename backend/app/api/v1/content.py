
import requests
from fastapi import APIRouter, HTTPException

from app.schemas.content import (
    ContentExtractRequest,
    ContentExtractResponse,
    SourceInfo,
    ImageAsset,
)
from app.services.content_extractor import (
    IMAGE_MARKER,
    image_marker,
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
    # 추출 순서(1부터) → 저장에 성공한 이미지 순서(1부터)
    renumber: dict[int, int] = {}

    for index, image_url in enumerate(content.image_urls, start=1):
        try:
            asset = save_image(image_url)
        except (ImageStorageError, requests.RequestException):
            # 이미지 저장 실패는 전체 추출 실패로 처리하지 않음
            continue

        renumber[index] = len(images) + 1

        images.append(
            ImageAsset(
                asset_id=str(asset.asset_id),
                url=asset.url,
                width=asset.width,
                height=asset.height,
                alt=None,
            )
        )

    # 본문의 "[이미지 N]"을 응답 images 순서에 맞추고, 저장 못 한 이미지 자리는 지운다
    def replace_marker(match) -> str:
        number = renumber.get(int(match.group(1)))
        return image_marker(number) if number else ""

    text = IMAGE_MARKER.sub(replace_marker, content.text)
    text = "\n".join(line for line in text.split("\n") if line.strip())

    # 3. 최종 API 응답 구성
    return ContentExtractResponse(
        source=SourceInfo(
            platform="naver_blog",
            blog_id=content.blog_id,
            log_no=content.log_no,
            url=content.url,
        ),
        title=content.title,
        text=text,
        images=images,
    )
