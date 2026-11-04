
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.storage import get_asset

router = APIRouter(prefix="/assets", tags=["Assets"])


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
