# blog2shorts
네이버 블로그 글을 AI 숏폼 영상으로 자동 변환

블로그 URL 또는 본문을 입력하면 AI가 핵심 내용을 분석해 숏폼 대본과 장면을 만들고, 사용자가 장면을 수정한 뒤 9:16 세로형 MP4 영상으로 받아보는 웹서비스 MVP입니다. (미니인턴 과제)

```
① 컨텐츠 가져오기 → ② 대본 구상하기 → ③ 장면 → ④ 음성과 음악 → ⑤ 영상 제작
```

진행 방식은 두 가지입니다.

- **장면 확인 후 만들기**: ①~③까지 만들고 멈춤 → 장면·목소리·배경음악을 확인/수정 → ④~⑤
- **처음부터 끝까지 자동**: ①~⑤를 한 번에. 완성 후 장면을 고쳐 다시 만들 수 있음

> 전체 흐름은 실제 API로 동작하며, `OPENAI_API_KEY`와 FFmpeg가 필요합니다. → [현재 구현 상태](#현재-구현-상태)

## 기술 스택

| 영역 | 사용 기술 |
|---|---|
| Frontend | React 19, TypeScript 7, Vite 8, CSS Modules, oxlint |
| Backend | Python 3.13, FastAPI, Pydantic v2, pydantic-settings, Uvicorn, uv |
| 테스트 | pytest, FastAPI TestClient |
| AI | OpenAI API — 대본 생성(Structured Outputs), TTS |
| 영상 | FFmpeg CLI (Python `subprocess`로 호출) |

선택 이유는 [docs/tech-decisions.md](docs/tech-decisions.md)에 있습니다.

## 문서

| 문서 | 내용 |
|---|---|
| [requirements.md](docs/requirements.md) | 요구사항, MVP 범위, 완료 조건 |
| [architecture.md](docs/architecture.md) | 시스템 구조, 추출·영상 생성 흐름, 저장·보안 |
| [api-design.md](docs/api-design.md) | REST API 설계 |
| [development-plan.md](docs/development-plan.md) | 단계별 개발 계획 |
| [tech-decisions.md](docs/tech-decisions.md) | 기술 의사결정 기록 |
| [design-system.md](docs/design-system.md) | 디자인 토큰·공통 컴포넌트·화면 작성 규칙 |

## 폴더 구조

```text
blog2shorts/
├── docs/                         # 요구사항·설계 문서
├── frontend/                     # React + TS + Vite
│   ├── .env.example
│   └── src/
│       ├── api/                  # fetch 클라이언트, API 함수
│       ├── components/
│       │   ├── common/           # 공통 UI (Button, Card, Tabs, TextField, Stack, Grid, Text, StepCard, RoleBadge, StatusBadge,
│       │   │                     #          SegmentedControl, Select, Range, SceneThumb, Dialog, VideoPlayer)
│       │   └── layout/           # PageLayout, SplitLayout
│       ├── features/
│       │   ├── pipeline/         # 5단계 상태(useReducer)·진행 방식
│       │   ├── content/          # ① 입력 폼(진행 방식 토글 포함), 가져온 원문
│       │   ├── script/           # ② 대본 요약
│       │   ├── editor/           # ③ 장면 확인·수정, 이미지 선택
│       │   ├── audio/            # ④ 목소리·배경음악 선택
│       │   └── video/            # ⑤ 진행 상태 줄, 완성 영상
│       ├── hooks/                # 공통 훅 (useHealthCheck)
│       ├── utils/                # scroll 등 작은 도우미
│       ├── pages/                # HomePage
│       ├── styles/               # CSS 변수, 전역 스타일
│       ├── types/                # API 타입
│       ├── App.tsx
│       └── main.tsx
├── backend/                      # FastAPI
│   ├── .env.example
│   ├── pyproject.toml / uv.lock
│   ├── app/
│   │   ├── main.py               # create_app(), CORS, 라우터 등록
│   │   ├── core/config.py        # 환경변수 설정 (pydantic-settings)
│   │   ├── api/v1/               # router.py, health.py
│   │   └── schemas/              # 요청/응답 Pydantic 모델
│   └── tests/
├── backend.sh / frontend.sh     # 개발 서버 실행 스크립트
├── .gitignore
└── README.md
```

화면은 [디자인 시스템](docs/design-system.md)의 토큰과 공통 컴포넌트만으로 만듭니다(페이지에 색·px·전용 CSS 금지). 공통 컴포넌트 규칙: 여러 곳에서 쓰거나 기능과 무관한 UI는 `components/common/<이름>/`(컴포넌트 + `index.ts`), 특정 기능 전용은 `features/<기능>/`에 둡니다. 백엔드 비즈니스 로직은 기능 구현 시 `app/services/`에 추가합니다.

## 사전 요구사항

- Node.js 20.19+ 또는 22.12+ (Vite 8 요구사항, 개발 환경은 Node 26에서 확인)
- [uv](https://docs.astral.sh/uv/) — Python 3.13이 없으면 `uv`가 자동으로 설치합니다
- FFmpeg (영상 합성, PATH에서 실행 가능해야 함)

## 설치 및 실행

터미널 두 개를 사용합니다.

### 빠른 실행 (스크립트)

```bash
./backend.sh     # 터미널 1 — http://localhost:8000
./frontend.sh    # 터미널 2 — http://localhost:5173
```

처음 실행하면 `.env.example`을 복사해 `backend/.env`, `frontend/.env.local`을 만들고 의존성을 설치한 뒤 개발 서버를 띄웁니다. 포트는 `PORT=8001 ./backend.sh`처럼 바꿀 수 있습니다. 백엔드 포트를 바꾸면 `frontend/.env.local`의 `VITE_API_BASE_URL`도 같이 바꿔야 합니다.

아래는 스크립트가 하는 일을 직접 실행하는 방법입니다.

### Backend

```bash
cd backend
cp .env.example .env          # 필요 시 값 수정
uv sync                       # .venv 생성 + 의존성 설치 (Python 3.13)
uv run uvicorn app.main:app --reload --port 8000
```

- Health: http://localhost:8000/api/v1/health
- Swagger UI: http://localhost:8000/docs
- OpenAPI 스키마: http://localhost:8000/openapi.json

### Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev                   # http://localhost:5173
```

첫 화면의 "백엔드 연결 상태"가 **연결됨**이면 정상입니다. 백엔드가 꺼져 있으면 **연결 실패**가 표시되고 "다시 확인"으로 재시도할 수 있습니다.

## 환경변수

### `backend/.env`

| 변수 | 기본값 | 설명 |
|---|---|---|
| `APP_ENV` | `development` | `development` \| `production` |
| `CORS_ORIGINS` | `["http://localhost:5173","http://127.0.0.1:5173"]` | 허용할 프론트엔드 Origin (JSON 배열) |
| `OPENAI_API_KEY` | (없음) | 대본·TTS 생성에 사용. **백엔드에만 설정** |
| `NAVER_BLOG_IDS` | `["copper567"]` | 허용할 네이버 블로그 ID (예약, 현재 미사용) |
| `STORAGE_DIR` | `backend/storage` | 이미지·영상 저장 경로 |

`OPENAI_SCRIPT_MODEL`(기본 `gpt-4.1-mini`), `OPENAI_TTS_MODEL`(기본 `tts-1`)로 모델을 바꿀 수 있습니다. 대본 모델은 이미지 입력을 지원해야 합니다.

배경음악은 라이선스를 확인한 음원을 `backend/assets/music/`에 넣으면 화면에 나타납니다. 자세한 내용은 [음원 안내](backend/assets/music/README.md)를 참고하세요.

실제 환경변수가 `.env` 값보다 우선합니다.

### `frontend/.env.local`

| 변수 | 예시 | 설명 |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | 백엔드 주소. 빌드 결과물에 포함되므로 비밀값 금지 |

`.env`, `.env.local` 등은 `.gitignore`로 제외되며 `.env.example`만 커밋합니다.

## 테스트·검사

```bash
# Backend
cd backend && uv run pytest

# Frontend
cd frontend
npm run build      # tsc -b 타입 검사 + 프로덕션 빌드
npm run lint       # oxlint
```

## 현재 구현 상태

| 항목 | 상태 |
|---|---|
| 요구사항·설계 문서 (`docs/`) | 완료 |
| Backend: FastAPI 앱, 설정, CORS, `GET /api/v1/health`, 테스트 4개 | 완료 |
| Frontend: 디자인 시스템(토큰·공통 컴포넌트 16종 + 레이아웃 2종), API 클라이언트 | 완료 |
| Frontend: 5단계 화면 흐름 + 진행 방식 토글(장면 확인 후 만들기 / 처음부터 끝까지 자동), 장면 편집, 목소리·배경음악 선택, 중지 | 완료 |
| 콘텐츠 입력·네이버 블로그 추출 (FR-01) | 완료 |
| AI 대본 생성 (FR-02) | 완료 |
| 장면 편집 (FR-03) | 프론트엔드 완료 (서버 저장 없음, 설계대로) |
| TTS·자막 (FR-04) | 완료 |
| 영상 합성 (FR-05) | 완료 |
| 미리보기·다운로드 (FR-06) | 완료 |
| 쇼츠 영상 디지인 (FR-7) | 구현중 | 

## 향후 개발 계획

자세한 작업과 완료 조건은 [docs/development-plan.md](docs/development-plan.md)를 참고하세요.

1. ~~프로젝트 초기 설정~~
2. ~~콘텐츠 입력 및 추출 — `copper567` 네이버 블로그 PostView 파싱, 본문 직접 입력~~
3. ~~AI 대본 생성 — OpenAI Structured Outputs, 장면 4~6개 검증~~
4. ~~장면 편집 — 문구·이미지 수정 (프론트엔드 상태)~~
5. ~~TTS 및 자막 — 장면별 음성, 자막 PNG~~
6. ~~영상 합성 — FFmpeg, 백그라운드 작업 + 상태 조회~~
7. ~~미리보기 및 다운로드~~
8. 테스트 및 배포
