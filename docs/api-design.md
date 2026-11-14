# API 설계 — Blog to Shorts

> 상태: 설계안 v0.1 (2026-11-03) · **구현된 엔드포인트는 `GET /api/v1/health` 하나**다. 나머지는 구현 전 설계이며 구현 과정에서 바뀔 수 있다. 구현된 API의 실제 스키마는 실행 중인 서버의 `/docs`(Swagger UI)와 `/openapi.json`이 기준이다.

## 공통 규칙

- Base URL: `{BACKEND}/api/v1` (로컬: `http://localhost:8000/api/v1`)
- 형식: JSON (`Content-Type: application/json`), 파일 응답 제외
- 필드명: `snake_case`
- 식별자: `asset_id`, `job_id`는 서버가 만든 UUID 문자열
- 인증: 없음 (MVP)

### 공통 오류 응답

```json
{
  "error": {
    "code": "UNSUPPORTED_URL",
    "message": "지원하지 않는 URL입니다. copper567 네이버 블로그 글 주소를 입력하거나 본문을 직접 입력해 주세요.",
    "details": null
  }
}
```

| HTTP | code | 의미 |
|---|---|---|
| 400 | `UNSUPPORTED_URL` | 허용되지 않은 도메인·blogId·형식 |
| 404 | `NOT_FOUND` | 존재하지 않거나 만료된 asset/job |
| 409 | `JOB_NOT_READY` | 렌더가 끝나지 않은 작업의 다운로드 요청 |
| 422 | `VALIDATION_ERROR` | 요청 본문 스키마 위반 (FastAPI 기본 422를 공통 포맷으로 변환, `details`에 필드 오류) |
| 422 | `EXTRACTION_FAILED` | 글을 가져왔지만 본문을 찾지 못함 (비공개·삭제·구조 변경) |
| 502 | `UPSTREAM_ERROR` | 블로그 서버 오류·타임아웃 |
| 502 | `AI_GENERATION_FAILED` | OpenAI 오류, 거절, 스키마 검증 실패 |
| 500 | `INTERNAL_ERROR` | 그 외 서버 오류 (내부 메시지 비노출) |
| 500 | `OPENAI_API_KEY_MISSING` | OpenAI API 키 미설정 |
| 502 | `OPENAI_API_KEY_EXPIRED` | OpenAI API 키 만료 |
| 502 | `OPENAI_API_KEY_INVALID` | OpenAI API 키가 올바르지 않음 |
| 502 | `OPENAI_PERMISSION_DENIED` | 이 키에 사용 권한 없음 |
| 502 | `OPENAI_QUOTA_EXCEEDED` | 크레딧·사용 한도 소진 |
| 502 | `OPENAI_RATE_LIMITED` | 요청 과다 |
| 502 | `OPENAI_MODEL_NOT_FOUND` | 모델을 사용할 수 없음 |
| 502 | `OPENAI_TIMEOUT` / `OPENAI_CONNECTION_FAILED` / `OPENAI_SERVER_ERROR` | OpenAI 응답 시간 초과 / 연결 실패 / 서버 오류 |
| 502 | `OPENAI_ERROR` | 그 외 OpenAI 오류 |

OpenAI 원문 메시지는 키 일부가 들어갈 수 있어 클라이언트에 그대로 보내지 않는다. 분류 구현은 `backend/app/core/errors.py`에 있다.

## 엔드포인트 요약

| # | Method | Path | 목적 | 상태 |
|---|---|---|---|---|
| 1 | GET | `/health` | 서버 상태 확인 | **구현됨** |
| 2 | POST | `/content/extract` | 블로그 URL에서 제목·본문·이미지 추출 | 설계 |
| 3 | GET | `/assets/{asset_id}` | 추출된 이미지 제공 | 설계 |
| 4 | POST | `/scripts/generate` | 콘텐츠로 숏폼 대본·장면 생성 | 설계 |
| 5 | POST | `/videos` | 편집된 장면으로 렌더 작업 생성 | 설계 |
| 6 | GET | `/videos/{job_id}` | 렌더 작업 상태 조회 | 설계 |
| 7 | GET | `/videos/{job_id}/download` | 완성 MP4 다운로드·미리보기 | 설계 |
| 8 | DELETE | `/videos/{job_id}` | 진행 중인 렌더 작업 중지 | **구현됨** |
| 9 | GET | `/audio/music` | 음원 파일이 있는 배경음악 목록 | **구현됨** |

요청서의 예시(`POST /videos/render`, `GET /videos/{job_id}/status`) 대비 변경점: 렌더 작업을 `videos` 리소스 생성으로 보고 `POST /videos`, 상태는 리소스 조회 `GET /videos/{job_id}`로 단순화했다. 이미지가 핫링크 제한을 받을 수 있어 `GET /assets/{asset_id}`를 추가했다.

**장면 편집 API는 두지 않는다.** 장면 데이터는 프론트엔드 상태로 관리하고, 렌더 요청에 편집본 전체를 담아 보낸다. 서버는 저장하지 않으므로 별도 조회·수정 API가 필요 없다.

---

## 1. `GET /api/v1/health` — 구현됨

- 목적: 백엔드 기동 여부·환경 확인 (프론트엔드 연결 확인에 사용)
- Request: 없음
- Response `200`

```json
{ "status": "ok", "app_env": "development", "version": "0.1.0" }
```

- 오류: 서버가 내려가 있으면 네트워크 오류(프론트엔드에서 "연결 실패" 표시)

## 2. `POST /api/v1/content/extract` - 구현됨 (feat/content-extraction 브랜치)

- 목적: 허용된 네이버 블로그 글 URL에서 제목·본문 텍스트·이미지를 추출
- Request

```json
{ "url": "https://blog.naver.com/copper567/224443571088" }
```

- Response `200`

```json
{
  "source": { "platform": "naver_blog", "blog_id": "copper567", "log_no": "224443571088", "url": "https://blog.naver.com/copper567/224443571088" },
  "title": "인디자인독학 실무자들은 이렇게 공부해요",
  "text": "본문 텍스트…",
  "images": [
    { "asset_id": "5b8e…", "url": "/api/v1/assets/5b8e…", "width": 966, "height": 644, "alt": null }
  ]
}
```

- 오류: `400 UNSUPPORTED_URL`, `422 VALIDATION_ERROR`, `422 EXTRACTION_FAILED`, `502 UPSTREAM_ERROR`
- 비고: 이미지 다운로드 일부가 실패해도 본문 추출이 성공하면 `200`(성공한 이미지만 반환). 본문을 직접 입력하는 경우 이 API를 호출하지 않는다.

## 3. `GET /api/v1/assets/{asset_id}` - 구현됨 (feat/content-extraction 브랜치)

- 목적: 추출 단계에서 서버에 저장한 이미지를 브라우저에 제공
- Request: path `asset_id`(UUID)
- Response `200`: 이미지 바이너리 (`image/jpeg` | `image/png` | `image/webp`)
- 오류: `404 NOT_FOUND`(없음·만료), `422 VALIDATION_ERROR`(UUID 형식 아님)

## 4. `POST /api/v1/scripts/generate` - 구현됨 (feat/script-generate 브랜치)

- 목적: 콘텐츠를 분석해 30~60초 숏폼 대본과 4~6개 장면 생성
- Request

```json
{
  "title": "인디자인독학 실무자들은 이렇게 공부해요",
  "text": "본문 텍스트 (200~20,000자)",
  "images": [ { "asset_id": "5b8e…", "alt": null } ],
  "target_duration_sec": 45
}
```

| 필드 | 규칙 |
|---|---|
| `title` | 선택, 최대 200자 |
| `text` | 필수, 200~20,000자 (설정값) |
| `images` | 선택, 최대 20개. 직접 입력 시 빈 배열 |
| `target_duration_sec` | 선택, 30~60, 기본 45 |

- Response `200`

```json
{
  "summary": { "topic": "인디자인 독학 방법", "key_points": ["…", "…", "…"] },
  "scenes": [
    { "order": 1, "role": "hook", "narration": "디자이너들은 인디자인을 어떻게 공부할까요?", "caption": "실무자는 이렇게 공부한다", "asset_id": "5b8e…" },
    { "order": 2, "role": "body", "narration": "…", "caption": "…", "asset_id": "…" },
    { "order": 3, "role": "body", "narration": "…", "caption": "…", "asset_id": null },
    { "order": 4, "role": "cta",  "narration": "…", "caption": "…", "asset_id": "…" }
  ],
  "estimated_duration_sec": 42
}
```

장면 스키마 규칙 (AI 응답 검증 기준):

| 규칙 | 내용 |
|---|---|
| 장면 수 | 4~6 |
| 순서 | `order`는 1부터 1씩 증가 |
| 역할 | 첫 장면 `hook`, 마지막 장면 `cta`, 사이는 모두 `body`(2~4개) |
| `narration` | 장면당 1~120자, 전체 약 150~350자 |
| `caption` | 장면당 1~30자 (화면 표시용 요약) |
| `subtitle_pages` | 내레이션을 나눈 영상 자막. `[["1줄", "2줄"], ["다음 자막"]]` 형식이고 자막마다 1~2줄. 항상 값이 있다 (AI 결과의 품질이 낮으면 서버 규칙으로 나눈다) |
| `asset_id` | 요청 `images`에 있는 값 또는 `null`(대체 배경) |
| `estimated_duration_sec` | 서버가 글자 수 기반으로 계산(AI 값 미사용) |

- 오류: `422 VALIDATION_ERROR`, `502 AI_GENERATION_FAILED`(OpenAI 오류·거절·스키마 위반 — 서버 내부 1회 재시도 후)

## 5. `POST /api/v1/videos` 구현예정

- 목적: 편집된 장면으로 TTS·자막·영상 합성 작업을 시작
- Request

```json
{
  "scenes": [
    { "order": 1, "role": "hook", "narration": "…", "caption": "…", "asset_id": "5b8e…", "subtitle_pages": [["1줄", "2줄"], ["다음 자막"]] }
  ],
  "hook_text": "…",
  "voice": "edge_injoon",
  "music": "none",
  "music_volume": 30
}
```

검증 규칙은 4번의 장면 규칙과 같다. `asset_id`는 존재하는 asset이어야 한다. `voice`는 Edge 음성 `edge_injoon` | `edge_sunhi` | `edge_hyunsu`(무료), Supertonic 로컬 음성 `supertonic_male` | `supertonic_female`(무료), OpenAI 음성 `calm_female` | `bright_female` | `clear_male` | `low_male`, 또는 `null`(기본 `edge_injoon`)이다. `music`은 `none` 또는 `GET /audio/music`의 곡 ID이고, `music_volume`은 0~100이다. `subtitle_pages`는 생략할 수 있고, 내레이션과 글자가 맞으면 그대로 영상 자막으로 쓴다 (맞지 않으면 서버가 규칙으로 다시 나눈다).

- Response `202`

```json
{ "job_id": "c1f2…", "status": "queued", "status_url": "/api/v1/videos/c1f2…" }
```

- 오류: `422 VALIDATION_ERROR`, `404 NOT_FOUND`(없는 asset_id, 음원 파일이 없는 곡)

## 6. `GET /api/v1/videos/{job_id}`

- 목적: 렌더 작업 진행 상태 조회 (프론트엔드가 2초 간격 폴링)
- 현재 구현 응답: `{ "job_id": "c1f2…", "status": "queued" | "processing" | "completed" | "failed" | "cancelled", "error": null | { "code", "message" } }`. `error.code`는 공통 오류 코드(OpenAI 키 만료 등)이거나 `TTS_FAILED`, `RENDER_FAILED`다. 아래는 최초 설계안이며 `step`·`progress` 등은 아직 구현되지 않았다.
- Response `200`

```json
{
  "job_id": "c1f2…",
  "status": "running",
  "step": "tts",
  "progress": 0.4,
  "duration_sec": null,
  "download_url": null,
  "error": null,
  "created_at": "2026-11-03T05:00:00Z",
  "updated_at": "2026-11-03T05:00:12Z"
}
```

| 필드 | 값 |
|---|---|
| `status` | `queued` \| `running` \| `succeeded` \| `failed` |
| `step` | `tts` \| `compose` \| `encode` \| `null` |
| `progress` | 0.0~1.0 |
| `download_url` | 성공 시 `/api/v1/videos/{job_id}/download` |
| `error` | 실패 시 `{ "code": "TTS_FAILED" \| "RENDER_FAILED", "message": "…" }` |

- 오류: `404 NOT_FOUND`(없는 작업, 서버 재시작으로 사라진 작업 포함)

## 7. `GET /api/v1/videos/{job_id}/download`

- 목적: 완성 영상 제공. `<video src>` 미리보기와 다운로드에 같이 사용
- Request: query `inline=true`면 미리보기(`Content-Disposition: inline`), 기본은 `attachment; filename="blog2shorts-{job_id}.mp4"`
- Response `200`: `video/mp4` 바이너리
- 오류: `404 NOT_FOUND`, `409 JOB_NOT_READY`

## 8. `DELETE /api/v1/videos/{job_id}`

- 목적: 진행 중인 렌더 작업 중지. 실행 중인 FFmpeg도 함께 종료한다
- Response `200`: `GET /videos/{job_id}`와 같은 형식. 이미 끝난 작업은 상태를 바꾸지 않는다
- 오류: `404 NOT_FOUND`

## 9. `GET /api/v1/audio/music`

- 목적: `backend/assets/music/`에 음원 파일이 있는 배경음악 목록 조회
- Response `200`: `{ "tracks": [{ "id": "soft_piano", "label": "잔잔한 피아노" }] }`
