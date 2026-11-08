"""대본 생성 서비스 테스트 (OpenAI 호출은 모킹)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from PIL import Image

from app.schemas.script import (
    ScriptGenerateRequest,
    ScriptImage,
    ScriptOutputFormat,
)
from app.services import script_generate
from app.services.script_prompts import SCRIPT_INSTRUCTIONS
from app.services.script_generate import (
    ScriptGenerationError,
    build_user_content,
    generate_script,
    load_image_data_url,
    normalize_narration_style,
    normalize_subtitle_pages,
)

BODY = "자동차정비기능사 시험을 공부할 때는 기본 구조부터 이해해야 합니다. " * 6

NARRATION = (
    "자동차 구조를 먼저 이해하고 기출문제를 반복해서 풀어 보세요. "
    "틀린 문제는 이론으로 돌아가 복습하는 게 좋아요."
)


def make_output(asset_ids: list[str | None]) -> ScriptOutputFormat:
    last = len(asset_ids) - 1

    return ScriptOutputFormat(
        summary={"topic": "주제", "key_points": ["핵심"]},
        hook_text="혼자 준비할 수 있을까요?",
        scenes=[
            {
                "order": index + 1,
                "role": (
                    "hook" if index == 0
                    else "cta" if index == last
                    else "body"
                ),
                "narration": NARRATION,
                "caption": "자막",
                "subtitle_pages": [],
                "asset_id": asset_id,
            }
            for index, asset_id in enumerate(asset_ids)
        ],
    )


def mock_client(*outputs: ScriptOutputFormat) -> Mock:
    client = Mock()
    client.close = AsyncMock()
    client.responses.parse = AsyncMock(
        side_effect=[
            SimpleNamespace(output_parsed=output)
            for output in outputs
        ]
    )
    return client


def make_request(asset_ids: list[str]) -> ScriptGenerateRequest:
    return ScriptGenerateRequest(
        title="제목",
        text=BODY,
        images=[
            ScriptImage(asset_id=asset_id)
            for asset_id in asset_ids
        ],
    )


def save_test_image(tmp_path, size=(2000, 1000)):
    path = tmp_path / "image.png"
    Image.new("RGB", size, "red").save(path)
    return path


# 1. 말투 교정
@pytest.mark.parametrize(
    "before,after",
    [
        ("이해하는 게 중요합니다.", "이해하는 게 중요해요."),
        ("도움이 됩니다!", "도움이 돼요!"),
        ("강의가 있습니다", "강의가 있어요"),
        ("이것이 요령입니다.", "이것이 요령이에요."),
        ("좋은 교재입니다.", "좋은 교재예요."),
        ("확인하시길 바랍니다.", "확인하시길 바라요."),
        ("이미 해요체예요.", "이미 해요체예요."),
    ],
)
def test_normalize_narration_style(before, after):
    assert normalize_narration_style(before) == after


# 2. AI에 보낼 이미지
def test_load_image_data_url_downscales_image(tmp_path):
    path = save_test_image(tmp_path)
    asset_id = str(uuid4())

    with patch.object(
        script_generate,
        "get_asset",
        return_value=Mock(path=path),
    ):
        data_url = load_image_data_url(asset_id)

    assert data_url.startswith("data:image/jpeg;base64,")


@pytest.mark.parametrize("asset_id", ["not-a-uuid", str(uuid4())])
def test_load_image_data_url_returns_none_for_unknown_asset(asset_id):
    with patch.object(script_generate, "get_asset", return_value=None):
        assert load_image_data_url(asset_id) is None


@pytest.mark.asyncio
async def test_build_user_content_includes_images_with_ids(tmp_path):
    path = save_test_image(tmp_path)
    asset_id = str(uuid4())

    with patch.object(
        script_generate,
        "get_asset",
        return_value=Mock(path=path),
    ):
        content = await build_user_content(make_request([asset_id]))

    assert [part["type"] for part in content] == [
        "input_text",
        "input_text",
        "input_image",
    ]
    assert asset_id in content[1]["text"]
    assert content[2]["image_url"].startswith("data:image/jpeg")


@pytest.mark.asyncio
async def test_build_user_content_skips_unreadable_image():
    with patch.object(script_generate, "get_asset", return_value=None):
        content = await build_user_content(make_request([str(uuid4())]))

    assert [part["type"] for part in content] == ["input_text"]


# 3. 대본 생성 흐름
@pytest.mark.asyncio
async def test_generate_script_fills_scene_without_image():
    ids = [str(uuid4()) for _ in range(5)]
    client = mock_client(
        make_output([ids[0], ids[1], ids[2], None])
    )

    with (
        patch.object(script_generate, "get_openai_client", return_value=client),
        patch.object(script_generate, "get_asset", return_value=None),
    ):
        result = await generate_script(make_request(ids))

    # 아직 쓰지 않은 이미지가 우선 배정된다
    assert result.scenes[3].asset_id == ids[3]


@pytest.mark.asyncio
async def test_generate_script_keeps_null_when_no_images():
    client = mock_client(make_output([None, None, None, None]))

    with patch.object(script_generate, "get_openai_client", return_value=client):
        result = await generate_script(make_request([]))

    assert all(scene.asset_id is None for scene in result.scenes)


@pytest.mark.asyncio
async def test_generate_script_normalizes_narration_style():
    output = make_output([None, None, None, None])
    output.scenes[0].narration = NARRATION + " 정말 중요합니다."
    client = mock_client(output)

    with patch.object(script_generate, "get_openai_client", return_value=client):
        result = await generate_script(make_request([]))

    assert result.scenes[0].narration.endswith("정말 중요해요.")


@pytest.mark.asyncio
async def test_generate_script_retries_unknown_image_id():
    known = str(uuid4())
    client = mock_client(
        make_output(["unknown", None, None, None]),
        make_output([known, known, known, known]),
    )

    with (
        patch.object(script_generate, "get_openai_client", return_value=client),
        patch.object(script_generate, "get_asset", return_value=None),
    ):
        result = await generate_script(make_request([known]))

    assert client.responses.parse.await_count == 2
    assert result.scenes[0].asset_id == known


@pytest.mark.asyncio
async def test_generate_script_fails_after_invalid_outputs():
    client = mock_client(
        make_output([None, None, None]),
        make_output([None, None, None]),
    )

    with (
        patch.object(script_generate, "get_openai_client", return_value=client),
        pytest.raises(ScriptGenerationError),
    ):
        await generate_script(make_request([]))

    client.close.assert_awaited_once()


# 4. AI가 나눈 자막
def test_normalize_subtitle_pages_keeps_valid_pages():
    pages = [["먼저 자동차 구조를", "차근차근 이해해 보세요."]]

    assert normalize_subtitle_pages(
        pages,
        "먼저 자동차 구조를 차근차근 이해해 보세요.",
    ) == pages


def test_normalize_subtitle_pages_applies_narration_style():
    narration = normalize_narration_style("자동차 구조를 먼저 차근차근 이해해야 합니다.")

    assert normalize_subtitle_pages(
        [["자동차 구조를 먼저", "차근차근 이해해야 합니다."]],
        narration,
    ) == [["자동차 구조를 먼저", "차근차근 이해해야 해요."]]


def test_normalize_subtitle_pages_falls_back_to_rule_split():
    assert normalize_subtitle_pages(
        [["내레이션과 다른 문장"]],
        "먼저 구조를 이해해 보세요.",
    ) == [["먼저 구조를 이해해 보세요."]]


@pytest.mark.asyncio
async def test_generate_script_returns_subtitle_pages():
    output = make_output([None, None, None, None])
    pages = [
        ["자동차 구조를 먼저 이해하고", "기출문제를 반복해서"],
        ["풀어 보세요."],
        ["틀린 문제는", "이론으로 돌아가"],
        ["복습하는 게 좋아요."],
    ]
    output.scenes[0].subtitle_pages = pages
    # 나머지 장면은 내레이션과 맞지 않는 자막이다
    output.scenes[1].subtitle_pages = [["엉뚱한 자막"]]
    client = mock_client(output)

    with patch.object(script_generate, "get_openai_client", return_value=client):
        result = await generate_script(make_request([]))

    assert result.scenes[0].subtitle_pages == pages
    # 쓸 수 없는 자막은 규칙으로 나눠서 항상 자막 단위를 돌려준다
    assert result.scenes[1].subtitle_pages
    assert result.scenes[1].subtitle_pages != [["엉뚱한 자막"]]


@pytest.mark.asyncio
async def test_generate_script_asks_ai_for_subtitle_pages():
    client = mock_client(make_output([None, None, None, None]))

    with patch.object(script_generate, "get_openai_client", return_value=client):
        await generate_script(make_request([]))

    instructions = client.responses.parse.await_args.kwargs["instructions"]

    assert "subtitle_pages" in instructions


def test_script_prompt_includes_each_section():
    """제목·말투·자막·이미지 지시가 프롬프트에 들어간다."""

    for keyword in ("hook_text", "해요체", "subtitle_pages", "asset_id"):
        assert keyword in SCRIPT_INSTRUCTIONS
