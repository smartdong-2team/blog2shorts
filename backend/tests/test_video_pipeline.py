from pathlib import Path
from uuid import uuid4
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.schemas.audio import (
    AudioAsset,
    AudioGenerationResult,
    SceneMedia,
    SubtitleCue,
)
from app.schemas.video import (
    VideoCreateRequest,
    VideoRenderResult,
)
from app.services import video_pipeline


@pytest.mark.asyncio
async def test_generate_video(monkeypatch, tmp_path):
    asset_id = uuid4()
    image_path = tmp_path / "image.jpg"
    image_path.write_bytes(b"fake-image")

    request = VideoCreateRequest(
        scenes=[
            {
                "order": 1,
                "role": "hook",
                "narration": "테스트 내레이션",
                "caption": "테스트 자막",
                "asset_id": asset_id,
            }
        ]
    )

    # 이미지 조회 모킹
    mock_asset = Mock(path=image_path)

    monkeypatch.setattr(
        video_pipeline,
        "get_asset",
        Mock(return_value=mock_asset),
    )

    # TTS 및 자막 생성 모킹
    audio_result = AudioGenerationResult(
        scenes=[
            SceneMedia(
                order=1,
                asset_id=str(asset_id),
                audio=AudioAsset(
                    path=str(tmp_path / "audio.wav"),
                    duration_sec=3.0,
                ),
                subtitles=[
                    SubtitleCue(
                        text="테스트 자막",
                        start_sec=0.0,
                        end_sec=3.0,
                    )
                ],
            )
        ],
        total_duration_sec=3.0,
    )

    mock_audio = AsyncMock(return_value=audio_result)

    monkeypatch.setattr(
        video_pipeline,
        "generate_scene_audio",
        mock_audio,
    )

    # 영상 렌더링 모킹
    output_path = tmp_path / "output.mp4"

    mock_render = AsyncMock(
        return_value=VideoRenderResult(
            path=output_path,
            duration_sec=3.0,
            width=1080,
            height=1920,
            fps=30,
        )
    )

    monkeypatch.setattr(
        video_pipeline,
        "render_video",
        mock_render,
    )

    result = await video_pipeline.generate_video(
        request=request,
        output_path=output_path,
        work_dir=tmp_path / "work",
    )

    assert result.path == output_path

    # 이미지 경로가 올바르게 연결되었는지 확인
    render_request = mock_render.call_args.args[0]

    assert len(render_request.scenes) == 1
    assert render_request.scenes[0].image_path == image_path
    # 화면 자막은 음성과 같은 내레이션을 장면 기준 시간으로 표시한다
    cues = render_request.scenes[0].subtitles
    assert cues[0].text == "테스트 내레이션"
    assert cues[0].start_sec == pytest.approx(0.0)
    assert cues[-1].end_sec == pytest.approx(3.0)

    # 목소리를 지정하지 않으면 기본 목소리를 사용한다
    assert mock_audio.await_args.kwargs["voice"] == "shimmer"

    # TTS 파이프라인이 호출되었는지 확인
    mock_audio.assert_awaited_once()



@pytest.mark.asyncio
async def test_generate_video_with_missing_asset(
    monkeypatch,
    tmp_path,
):
    asset_id = uuid4()

    request = VideoCreateRequest(
        scenes=[
            {
                "order": 1,
                "role": "hook",
                "narration": "테스트 내레이션",
                "caption": "테스트 자막",
                "asset_id": asset_id,
            }
        ]
    )

    # 존재하지 않는 이미지로 설정
    mock_get_asset = Mock(return_value=None)

    monkeypatch.setattr(
        video_pipeline,
        "get_asset",
        mock_get_asset,
    )

    # 이미지가 없으면 TTS와 렌더링이 실행되지 않아야 함
    mock_audio = AsyncMock()
    mock_render = Mock()

    monkeypatch.setattr(
        video_pipeline,
        "generate_scene_audio",
        mock_audio,
    )

    monkeypatch.setattr(
        video_pipeline,
        "render_video",
        mock_render,
    )

    output_path = tmp_path / "output.mp4"

    # 오류 발생 확인
    with pytest.raises(
        ValueError,
        match="이미지를 찾을 수 없습니다",
    ):
        await video_pipeline.generate_video(
            request=request,
            output_path=output_path,
            work_dir=tmp_path / "work",
        )

    # 올바른 asset_id로 조회했는지
    mock_get_asset.assert_called_once_with(asset_id)

    # 불필요한 작업이 실행되지 않았는지
    mock_audio.assert_not_awaited()
    mock_render.assert_not_called()

    # 결과 파일이 생성되지 않았는지
    assert not output_path.exists()


@pytest.mark.asyncio
async def test_generate_video_uses_ai_subtitle_pages(monkeypatch, tmp_path):
    asset_id = uuid4()
    pages = [["테스트", "내레이션"]]

    request = VideoCreateRequest(
        scenes=[
            {
                "order": 1,
                "role": "hook",
                "narration": "테스트 내레이션",
                "caption": "자막",
                "asset_id": asset_id,
                "subtitle_pages": pages,
            }
        ]
    )

    monkeypatch.setattr(
        video_pipeline,
        "get_asset",
        Mock(return_value=Mock(path=tmp_path / "image.jpg")),
    )
    monkeypatch.setattr(
        video_pipeline,
        "generate_scene_audio",
        AsyncMock(
            return_value=AudioGenerationResult(
                scenes=[
                    SceneMedia(
                        order=1,
                        asset_id=str(asset_id),
                        audio=AudioAsset(path="audio.wav", duration_sec=3.0),
                        subtitles=[
                            SubtitleCue(text="자막", start_sec=0.0, end_sec=3.0)
                        ],
                    )
                ],
                total_duration_sec=3.0,
            )
        ),
    )
    mock_render = AsyncMock()
    monkeypatch.setattr(video_pipeline, "render_video", mock_render)

    await video_pipeline.generate_video(
        request=request,
        output_path=tmp_path / "output.mp4",
        work_dir=tmp_path / "work",
    )

    cue = mock_render.await_args.args[0].scenes[0].subtitles[0]
    assert cue.text == "테스트\n내레이션"



@pytest.mark.asyncio
async def test_generate_video_reports_progress(monkeypatch, tmp_path):
    asset_id = uuid4()
    request = VideoCreateRequest(
        scenes=[
            {"order": 1, "role": "hook", "narration": "첫 장면", "caption": "첫", "asset_id": asset_id},
            {"order": 2, "role": "cta", "narration": "둘째 장면", "caption": "둘", "asset_id": asset_id},
        ]
    )
    monkeypatch.setattr(video_pipeline, "get_asset", Mock(return_value=Mock(path=tmp_path / "image.jpg")))

    async def fake_audio(scenes, output_dir, voice, on_scene_done=None):
        for done in (1, 2):
            on_scene_done(done, 2)
        return AudioGenerationResult(
            scenes=[
                SceneMedia(
                    order=order,
                    asset_id=str(asset_id),
                    audio=AudioAsset(path="audio.wav", duration_sec=2.0),
                    subtitles=[SubtitleCue(text="자막", start_sec=0.0, end_sec=2.0)],
                )
                for order in (1, 2)
            ],
            total_duration_sec=4.0,
        )

    async def fake_render(render_request, on_scene_done=None):
        for done in (1, 2):
            on_scene_done(done, 2)

    monkeypatch.setattr(video_pipeline, "generate_scene_audio", fake_audio)
    monkeypatch.setattr(video_pipeline, "render_video", fake_render)

    reported = []
    await video_pipeline.generate_video(
        request=request,
        output_path=tmp_path / "output.mp4",
        work_dir=tmp_path / "work",
        on_progress=reported.append,
    )

    assert [(p.stage, p.done, p.total) for p in reported] == [
        ("tts", 0, 2),
        ("tts", 1, 2),
        ("tts", 2, 2),
        ("rendering", 0, 2),
        ("rendering", 1, 2),
        ("finishing", 2, 2),
    ]
    progresses = [p.progress for p in reported]
    assert progresses == sorted(progresses)
    assert progresses[-1] == pytest.approx(0.95)
