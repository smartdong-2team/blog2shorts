"""NVIDIA 대본 생성 클라이언트와 제공자 선택 테스트 (실제 호출은 모킹)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import BaseModel, SecretStr

from app.core import nvidia
from app.core.errors import classify_error
from app.core.nvidia import (
    NvidiaClient,
    NvidiaKeyMissingError,
    get_nvidia_client,
    parse_json_output,
    to_chat_content,
)
from app.schemas.script import ScriptOutputFormat
from app.services import script_generate


def test_to_chat_content_converts_text_and_image():
    content = [
        {"type": "input_text", "text": "본문"},
        {"type": "input_image", "image_url": "data:image/jpeg;base64,AAA", "detail": "low"},
    ]

    assert to_chat_content(content) == [
        {"type": "text", "text": "본문"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,AAA"}},
    ]
    assert to_chat_content("다시 만들어") == "다시 만들어"


def test_parse_json_output_reads_json_inside_text():
    raw = '결과입니다\n```json\n{"winner": "1"}\n```'

    class Pick(BaseModel):
        winner: str

    assert parse_json_output(raw, Pick).winner == "1"
    assert parse_json_output("JSON 없음", Pick) is None
    assert parse_json_output('{"other": 1}', Pick) is None


@pytest.mark.asyncio
async def test_nvidia_client_sends_chat_request_with_schema():
    client = NvidiaClient("key")
    create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))]
        )
    )
    client._client.chat.completions.create = create

    result = await client.responses.parse(
        model="nvidia/model",
        instructions="규칙",
        input=[{"role": "user", "content": [{"type": "input_text", "text": "본문"}]}],
        text_format=ScriptOutputFormat,
    )

    kwargs = create.await_args.kwargs
    assert kwargs["model"] == "nvidia/model"
    assert kwargs["messages"][0] == {"role": "system", "content": "규칙"}
    assert kwargs["messages"][1]["content"] == [{"type": "text", "text": "본문"}]
    assert kwargs["response_format"]["json_schema"]["schema"] == ScriptOutputFormat.model_json_schema()
    assert "temperature" not in kwargs
    # 빈 JSON은 스키마 검증에 실패하므로 결과 없음
    assert result.output_parsed is None
    await client.close()


def test_get_nvidia_client_requires_key():
    with patch.object(nvidia, "get_settings", return_value=SimpleNamespace(nvidia_api_key=None)):
        with pytest.raises(NvidiaKeyMissingError):
            get_nvidia_client()


def test_missing_nvidia_key_has_its_own_error_code():
    error = classify_error(NvidiaKeyMissingError("없음"))

    assert error.code == "NVIDIA_API_KEY_MISSING"


@pytest.mark.parametrize(
    ("provider", "model"),
    [("openai", "gpt-model"), ("nvidia", "nvidia-model")],
)
def test_get_script_client_follows_provider_setting(provider, model):
    settings = SimpleNamespace(
        script_provider=provider,
        openai_script_model="gpt-model",
        nvidia_script_model="nvidia-model",
        nvidia_api_key=SecretStr("key"),
    )
    openai_client, nvidia_client = Mock(), Mock()

    with (
        patch.object(script_generate, "get_settings", return_value=settings),
        patch.object(script_generate, "get_openai_client", return_value=openai_client),
        patch.object(script_generate, "get_nvidia_client", return_value=nvidia_client),
    ):
        client, chosen = script_generate.get_script_client()

    assert client is (nvidia_client if provider == "nvidia" else openai_client)
    assert chosen == model


def test_script_schema_limits_asset_id_to_given_images():
    schema = script_generate.script_schema_with_image_ids(["a", "b"])
    asset_id = schema["$defs"]["ScriptOutputScene"]["properties"]["asset_id"]

    assert asset_id == {"anyOf": [{"enum": ["a", "b"]}, {"type": "null"}]}
    # 원래 스키마는 그대로 둔다
    assert "anyOf" in ScriptOutputFormat.model_json_schema()["$defs"]["ScriptOutputScene"]["properties"]["asset_id"]
    assert "enum" not in str(ScriptOutputFormat.model_json_schema()["$defs"]["ScriptOutputScene"]["properties"]["asset_id"])
