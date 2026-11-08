
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi import Response

from app.core.config import get_settings
from app.core.errors import classify_error
from app.schemas.video import VideoCreateRequest
from app.services.video_pipeline import generate_video
from app.services.storage import get_asset


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["videos"])

OUTPUT_DIR = get_settings().storage_dir / "videos"

# 임시 작업 저장소
# 이후 GET /videos/{job_id}에서도 사용
video_jobs: dict[str, dict] = {}


class VideoCreateResponse(BaseModel):
    job_id: str
    status: str
    status_url: str


class VideoJobError(BaseModel):
    code: str
    message: str


class VideoStatusResponse(BaseModel):
    job_id: str
    status: str
    error: VideoJobError | None = None


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
        )

        video_jobs[job_id]["status"] = "completed"
        video_jobs[job_id]["output_path"] = str(output_path)

    except Exception as exc:
        logger.exception("영상 생성 실패: %s", job_id)
        error = classify_error(exc)
        video_jobs[job_id]["status"] = "failed"
        video_jobs[job_id]["error"] = (
            # 파이프라인이 직접 올린 예외는 메시지가 곧 실패 원인이다.
            VideoJobError(
                code="RENDER_FAILED",
                message=f"영상 생성에 실패했습니다: {exc}",
            )
            if error.code == "INTERNAL_ERROR"
            else VideoJobError(code=error.code, message=error.message)
        )


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



@router.get("/{job_id}", response_model=VideoStatusResponse)
async def read_video_status(job_id: str):
    """영상 생성 작업의 상태와 실패 원인을 돌려준다."""

    job = video_jobs.get(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="영상 작업을 찾을 수 없습니다.",
        )

    return VideoStatusResponse(
        job_id=job_id,
        status=job["status"],
        error=job["error"],
    )


@router.head("/{job_id}/download")
async def check_video_ready(job_id: str):
    job = video_jobs.get(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="영상 작업을 찾을 수 없습니다.",
        )

    if job["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail="영상이 아직 생성 중입니다.",
        )

    if not Path(job["output_path"]).is_file():
        raise HTTPException(
            status_code=404,
            detail="영상 파일을 찾을 수 없습니다.",
        )

    return Response(status_code=200)

# 영상 생성 상태 조회 API
@router.get("/{job_id}/download")
async def download_video(job_id: str):
    job = video_jobs.get(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="영상 작업을 찾을 수 없습니다.",
        )

    if job["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail="영상 생성이 아직 완료되지 않았습니다.",
        )

    output_path = Path(job["output_path"])

    if not output_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="영상 파일을 찾을 수 없습니다.",
        )

    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        filename=f"{job_id}.mp4",
        content_disposition_type="inline",
    )