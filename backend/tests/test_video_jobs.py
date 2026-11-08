"""영상 작업 API 테스트: 배경음악 검증, 중지, 임시 파일 정리."""

import asyncio
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import videos
from app.api.v1.videos import run_video_job, video_jobs
from app.main import app
from app.schemas.video import VideoCreateRequest

client = TestClient(app)

VIDEO_URL = "/api/v1/videos"


def scene_payload() -> dict:
    return {
        "order": 1,
        "role": "hook",
        "narration": "내레이션",
        "caption": "자막",
        "asset_id": str(uuid4()),
    }


def make_job(status: str = "queued") -> str:
    job_id = str(uuid4())
    video_jobs[job_id] = {
        "status": status,
        "output_path": None,
        "error": None,
        "task": None,
    }
    return job_id


@pytest.fixture(autouse=True)
def clean_jobs():
    yield
    video_jobs.clear()


def test_create_video_rejects_missing_music_file():
    with (
        patch("app.api.v1.videos.get_asset", return_value=object()),
        patch("app.api.v1.videos.find_track", return_value=None),
    ):
        response = client.post(
            VIDEO_URL,
            json={"scenes": [scene_payload()], "music": "soft_piano"},
        )

    assert response.status_code == 404
    assert "배경음악" in response.json()["error"]["message"]


def test_cancel_unknown_job_returns_404():
    assert client.delete(f"{VIDEO_URL}/{uuid4()}").status_code == 404


def test_cancel_queued_job():
    job_id = make_job()

    response = client.delete(f"{VIDEO_URL}/{job_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


@pytest.mark.parametrize("status", ["completed", "failed"])
def test_cancel_finished_job_keeps_status(status):
    job_id = make_job(status)

    response = client.delete(f"{VIDEO_URL}/{job_id}")

    assert response.json()["status"] == status


def test_cancelled_job_is_not_downloadable():
    job_id = make_job("cancelled")

    assert client.get(f"{VIDEO_URL}/{job_id}/download").status_code == 409


def make_request() -> VideoCreateRequest:
    return VideoCreateRequest(scenes=[scene_payload()])


@pytest.mark.asyncio
async def test_run_video_job_skips_cancelled_job():
    job_id = make_job("cancelled")

    with patch("app.api.v1.videos.generate_video") as generate:
        await run_video_job(job_id, make_request())

    generate.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_stops_running_pipeline_and_cleans_up(tmp_path, monkeypatch):
    monkeypatch.setattr(videos, "OUTPUT_DIR", tmp_path)

    job_id = make_job()
    work_dir = tmp_path / "work" / job_id
    pipeline_started = asyncio.Event()

    async def slow_pipeline(request, output_path, work_dir):
        work_dir.mkdir(parents=True)
        pipeline_started.set()
        await asyncio.Event().wait()

    with patch("app.api.v1.videos.generate_video", slow_pipeline):
        job_task = asyncio.create_task(
            run_video_job(job_id, make_request())
        )
        await pipeline_started.wait()

        await videos.cancel_video(job_id)
        await job_task

    assert video_jobs[job_id]["status"] == "cancelled"
    assert not work_dir.exists()


@pytest.mark.asyncio
async def test_completed_job_removes_work_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(videos, "OUTPUT_DIR", tmp_path)

    job_id = make_job()
    work_dir = tmp_path / "work" / job_id

    async def quick_pipeline(request, output_path, work_dir):
        work_dir.mkdir(parents=True)

    with patch("app.api.v1.videos.generate_video", quick_pipeline):
        await run_video_job(job_id, make_request())

    assert video_jobs[job_id]["status"] == "completed"
    assert not work_dir.exists()


def test_browser_can_send_cancel_request():
    """브라우저의 사전 요청(CORS)이 중지 요청을 허용한다."""

    job_id = make_job()

    response = client.options(
        f"{VIDEO_URL}/{job_id}",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "DELETE",
        },
    )

    assert response.status_code == 200
    assert "DELETE" in response.headers["access-control-allow-methods"]
