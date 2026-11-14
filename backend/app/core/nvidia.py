"""NVIDIA API(build.nvidia.com) 클라이언트.

NVIDIA는 OpenAI의 Responses API를 지원하지 않으므로, 대본 생성 코드가 그대로 쓸 수 있게
`client.responses.parse(...)` 모양을 Chat Completions + JSON 스키마 호출로 바꿔 준다.
"""

import re
from types import SimpleNamespace

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


class NvidiaKeyMissingError(RuntimeError):
    """NVIDIA_API_KEY가 설정되지 않은 경우."""


def to_chat_content(content: str | list[dict]) -> str | list[dict]:
    """Responses 형식의 메시지 조각(input_text, input_image)을 Chat Completions 형식으로 바꾼다."""

    if isinstance(content, str):
        return content

    parts = []
    for part in content:
        if part["type"] == "input_text":
            parts.append({"type": "text", "text": part["text"]})
        elif part["type"] == "input_image":
            parts.append({"type": "image_url", "image_url": {"url": part["image_url"]}})
    return parts


def parse_json_output(raw: str, text_format: type[BaseModel]) -> BaseModel | None:
    """응답 글에서 JSON 객체를 꺼내 검증한다. 형식이 틀리면 None (호출한 쪽이 재시도한다)."""

    match = re.search(r"\{.*\}", raw, re.S)
    if match is None:
        return None
    try:
        return text_format.model_validate_json(match.group(0))
    except ValidationError:
        return None


class _Responses:
    def __init__(self, client: AsyncOpenAI):
        self._client = client

    async def parse(
        self,
        *,
        model: str,
        instructions: str,
        input: list[dict],
        text_format: type[BaseModel],
        temperature: float | None = None,
        json_schema: dict | None = None,
    ) -> SimpleNamespace:
        """json_schema를 주면 text_format 대신 그 스키마로 출력을 묶는다 (값 목록 제한 등)."""

        messages = [{"role": "system", "content": instructions}] + [
            {"role": message["role"], "content": to_chat_content(message["content"])} for message in input
        ]
        options = {} if temperature is None else {"temperature": temperature}
        response = await self._client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=4000,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": text_format.__name__, "schema": json_schema or text_format.model_json_schema()},
            },
            # 생각 과정을 출력하지 않게 해 JSON만 받는다
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            **options,
        )
        raw = response.choices[0].message.content or ""
        return SimpleNamespace(output_parsed=parse_json_output(raw, text_format))


class NvidiaClient:
    """대본 생성용 NVIDIA 클라이언트. OpenAI 클라이언트처럼 responses.parse와 close를 쓴다."""

    def __init__(self, api_key: str):
        self._client = AsyncOpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key, max_retries=0, timeout=120)
        self.responses = _Responses(self._client)

    async def close(self) -> None:
        await self._client.close()


def get_nvidia_client() -> NvidiaClient:
    """설정된 API 키로 NVIDIA 클라이언트를 만든다."""

    key = get_settings().nvidia_api_key
    if key is None or not key.get_secret_value():
        raise NvidiaKeyMissingError("NVIDIA_API_KEY가 설정되지 않았습니다.")
    return NvidiaClient(key.get_secret_value())
