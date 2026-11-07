from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.services.storage import (
    MAX_IMAGE_SIZE,
    ImageStorageError,
    get_asset,
    save_uploaded_image,
)

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.post("/upload", status_code=201)
async def upload_asset(file: UploadFile = File(...)):
    # 파일을 최대 허용 크기보다 1바이트 더 읽어 용량 초과 확인
    image_bytes = await file.read(MAX_IMAGE_SIZE + 1)
    await file.close()

    try:
        asset = save_uploaded_image(image_bytes)
    except ImageStorageError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_IMAGE",
                "message": str(exc),
            },
        ) from exc

    return {
        "asset_id": str(asset.asset_id),
        "url": asset.url,
        "width": asset.width,
        "height": asset.height,
    }


@router.get("/{asset_id}", response_class=FileResponse)
def read_asset(asset_id: UUID):
    asset = get_asset(asset_id)

    if asset is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_FOUND",
                "message": "이미지를 찾을 수 없습니다.",
            },
        )

    return FileResponse(
        path=asset.path,
        media_type=asset.media_type,
    )