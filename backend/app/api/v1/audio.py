from fastapi import APIRouter

from app.services.music import available_tracks

router = APIRouter(prefix="/audio", tags=["audio"])


@router.get("/music")
def list_music():
    """실제 음원 파일이 있는 배경음악 목록을 돌려준다."""

    return {"tracks": available_tracks()}
