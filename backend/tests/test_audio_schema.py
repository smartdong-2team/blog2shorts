
import pytest
from pydantic import ValidationError

from app.schemas.audio import (
    AudioAsset,
    SubtitleCue,
    SceneMedia,
    AudioGenerationResult,
)


def make_scene(
    order: int = 1,
    start_sec: float = 0.0,
    end_sec: float = 5.0,
) -> SceneMedia:
    """테스트에서 사용할 기본 장면을 생성한다."""
    return SceneMedia(
        order=order,
        asset_id="test-asset-id",
        audio=AudioAsset(
            path=f"scene_{order:02d}.mp3",
            duration_sec=end_sec - start_sec,
        ),
        subtitles=[
            SubtitleCue(
                text="테스트 자막입니다.",
                start_sec=start_sec,
                end_sec=end_sec,
            )
        ],
    )



# --------------------------------------------------
# 1. 음성 파일 경로가 비어 있지 않고 길이가 양수인지
# --------------------------------------------------
def test_audio_asset_accepts_valid_data():
    audio = AudioAsset(
        path="scene_01.mp3",
        duration_sec=5.2,
    )

    assert audio.path == "scene_01.mp3"
    assert audio.duration_sec == 5.2


@pytest.mark.parametrize("duration", [0, -1])
def test_audio_asset_rejects_invalid_duration(duration):
    with pytest.raises(ValidationError):
        AudioAsset(
            path="scene_01.mp3",
            duration_sec=duration,
        )


def test_audio_asset_rejects_empty_path():
    with pytest.raises(ValidationError):
        AudioAsset(
            path="",
            duration_sec=5.0,
        )



# --------------------------------------------------
# 2. 자막 텍스트가 존재하고 종료 시간이 시작 시간보다 큰지
# --------------------------------------------------
def test_subtitle_accepts_valid_timing():
    subtitle = SubtitleCue(
        text="첫 번째 자막",
        start_sec=0.0,
        end_sec=5.0,
    )

    assert subtitle.start_sec == 0.0
    assert subtitle.end_sec == 5.0


@pytest.mark.parametrize(
    "start_sec,end_sec",
    [
        (-1.0, 5.0),  # 음수 시작 시간
        (5.0, 5.0),   # 시작과 종료가 같음
        (6.0, 5.0),   # 종료가 시작보다 빠름
    ],
)
def test_subtitle_rejects_invalid_timing(start_sec, end_sec):
    with pytest.raises(ValidationError):
        SubtitleCue(
            text="잘못된 자막",
            start_sec=start_sec,
            end_sec=end_sec,
        )


def test_subtitle_rejects_empty_text():
    with pytest.raises(ValidationError):
        SubtitleCue(
            text="",
            start_sec=0.0,
            end_sec=5.0,
        )



# --------------------------------------------------
# 3. 장면 번호가 1 이상이고 자막이 하나 이상인지
# --------------------------------------------------
def test_scene_media_accepts_valid_data():
    scene = make_scene()

    assert scene.order == 1
    assert scene.audio.duration_sec == 5.0
    assert len(scene.subtitles) == 1


def test_scene_media_rejects_invalid_order():
    with pytest.raises(ValidationError):
        make_scene(order=0)


def test_scene_media_rejects_empty_subtitles():
    with pytest.raises(ValidationError):
        SceneMedia(
            order=1,
            asset_id=None,
            audio=AudioAsset(
                path="scene_01.mp3",
                duration_sec=5.0,
            ),
            subtitles=[],
        )



# --------------------------------------------------
# 4. 장면이 존재하고 번호가 1부터 연속적으로 증가하는지
# --------------------------------------------------
def test_audio_generation_result_accepts_valid_scenes():
    result = AudioGenerationResult(
        scenes=[
            make_scene(order=1, start_sec=0.0, end_sec=5.0),
            make_scene(order=2, start_sec=5.0, end_sec=11.0),
        ],
        total_duration_sec=11.0,
    )

    assert len(result.scenes) == 2
    assert result.total_duration_sec == 11.0
    assert [scene.order for scene in result.scenes] == [1, 2]


@pytest.mark.parametrize(
    "orders",
    [
        [2, 1],     # 순서가 뒤바뀜
        [1, 3],     # 순서가 건너뜀
        [1, 1],     # 순서가 중복됨
    ],
)
def test_audio_generation_result_rejects_invalid_order(orders):
    with pytest.raises(ValidationError):
        AudioGenerationResult(
            scenes=[
                make_scene(order=order)
                for order in orders
            ],
            total_duration_sec=10.0,
        )


def test_audio_generation_result_rejects_empty_scenes():
    with pytest.raises(ValidationError):
        AudioGenerationResult(
            scenes=[],
            total_duration_sec=5.0,
        )


@pytest.mark.parametrize("duration", [0, -1])
def test_audio_generation_result_rejects_invalid_duration(duration):
    with pytest.raises(ValidationError):
        AudioGenerationResult(
            scenes=[make_scene()],
            total_duration_sec=duration,
        )
