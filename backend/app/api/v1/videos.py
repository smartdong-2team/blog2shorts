
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.schemas.video import VideoCreateRequest
from app.services.video_pipeline import generate_video
from app.services.storage import get_asset


router = APIRouter(prefix="/videos", tags=["videos"])

OUTPUT_DIR = Path("output/videos")

# 임시 작업 저장소
# 이후 GET /videos/{job_id}에서도 사용
video_jobs: dict[str, dict] = {}


class VideoCreateResponse(BaseModel):
    job_id: str
    status: str
    status_url: str


async def run_video_job(
    job_id: str,
    request: VideoCreateRequest,
):
    """백그라운드 영상 생성 작업."""

    video_jobs[job_id]["status"] = "processing"

    output_path = OUTPUT_DIR / f"{job_id}.mp4"
    work_dir = OUTPUT_DIR / "work" / job_id

    try:
        await generate_video(
            request=request,
            output_path=output_path,
            work_dir=work_dir,
            font_file=Path(
                "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
            ),
        )

        video_jobs[job_id]["status"] = "completed"
        video_jobs[job_id]["output_path"] = str(output_path)

    except Exception as exc:
        video_jobs[job_id]["status"] = "failed"
        video_jobs[job_id]["error"] = str(exc)


@router.post(
    "",
    response_model=VideoCreateResponse,
    status_code=202,
)
async def create_video(
    request: VideoCreateRequest,
    background_tasks: BackgroundTasks,
):
    """편집된 장면을 받아 영상 생성 작업을 시작한다."""

    # 1. asset_id 존재 여부 검증
    for scene in request.scenes:
        asset = get_asset(scene.asset_id)

        if asset is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "NOT_FOUND",
                    "message": "이미지를 찾을 수 없습니다.",
                    "asset_id": str(scene.asset_id),
                },
            )

    # 2. 작업 ID 생성
    job_id = str(uuid4())

    # 3. 작업 상태 저장
    video_jobs[job_id] = {
        "status": "queued",
        "output_path": None,
        "error": None,
    }

    # 4. 백그라운드 작업 등록
    background_tasks.add_task(
        run_video_job,
        job_id,
        request,
    )

    # 5. 즉시 202 응답
    return VideoCreateResponse(
        job_id=job_id,
        status="queued",
        status_url=f"/api/v1/videos/{job_id}",
    )
