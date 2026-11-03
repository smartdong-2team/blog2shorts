# 기술 의사결정 기록 — Blog to Shorts

> 2026-11-03 작성. 공식 문서 조사 결과 중 **실제 설계에 반영한 내용만** 기록한다.
> 조사 한계: OpenAI API 키 안전 가이드(help.openai.com)는 403으로 열리지 않아 원문을 확인하지 못했다. FFmpeg 필터 문서는 분량이 커 `subtitles`/`drawtext` 절을 끝까지 읽지 못했고, 해당 판단은 로컬 FFmpeg 빌드 확인 결과로 내렸다.

## 확정된 결정

### D-01. Frontend: Vite + React + TypeScript
- 결정: `create-vite`(9.3)의 `react-ts` 템플릿으로 시작하고 템플릿의 tsconfig·린트 설정을 그대로 쓴다. 생성 결과: React 19.3, Vite 8.3, TypeScript 7.0, 린터 **oxlint**.
- 이유: SPA 하나면 충분하고 SSR이 필요 없다. 공식 템플릿을 쓰면 설정 유지 비용이 가장 적다. Next.js는 서버 기능이 백엔드와 겹쳐 도입하지 않는다.
- 반영한 공식 문서 내용 ([Vite Env Variables and Modes](https://vite.dev/guide/env-and-mode)):
  - 클라이언트에는 `VITE_` 접두사 변수만 노출되고, 이 값은 빌드 결과물에 그대로 들어간다 → 프론트엔드 env에는 `VITE_API_BASE_URL`만 두고 비밀값은 넣지 않는다.
  - `.env.local`, `.env.[mode].local`로 로컬 값을 분리할 수 있다 → 저장소에는 `.env.example`만 커밋한다.
  - 사용자 정의 변수 타입은 `src/vite-env.d.ts`에서 `ImportMetaEnv`를 확장한다.

### D-01-1. 린터: ESLint 대신 oxlint (요청서와 다른 결정)
- 결정: 템플릿 기본값인 oxlint(`.oxlintrc.json`, `npm run lint`)를 쓰고 ESLint는 설치하지 않는다.
- 이유: 현재 `create-vite` react-ts 템플릿은 ESLint 대신 oxlint를 생성하고, TypeScript 7.0을 사용한다. ESLint로 TS를 검사하는 `typescript-eslint`(8.72)는 peer 의존성이 `typescript >=4.8.4 <6.1.0`이라 TS 7과 함께 쓸 수 없다(`npm view typescript-eslint peerDependencies`로 확인). ESLint를 쓰려면 TypeScript를 6.0으로 내려야 한다.
- oxlint 설정에는 템플릿 기본 규칙(`react/rules-of-hooks`, `react/only-export-components`)이 포함되어 있다.
- 다시 검토할 조건: typescript-eslint가 TS 7을 지원하거나, 팀이 ESLint 전용 규칙(플러그인)을 필요로 할 때.

### D-02. Frontend 폴더 구조: 공통 컴포넌트 + 기능 폴더
- 결정: `components/common`(재사용 UI), `components/layout`(레이아웃), `features/<기능>`(기능 전용 컴포넌트·훅), `api/`(HTTP), `hooks/`(공통 훅), `pages/`, `types/`, `styles/`.
- 규칙: 2곳 이상에서 쓰거나 도메인과 무관한 UI → `components/common`. 특정 기능 전용 → `features/<기능>/`. 공통 컴포넌트는 `컴포넌트명/컴포넌트명.tsx + index.ts`.
- 디자인: 팀 데모(smartdong-demo) 톤을 기준으로 한 [design-system.md](design-system.md)를 따른다. 페이지·feature는 공통 컴포넌트만 조합한다.
- 스타일: Vite 기본 지원 CSS Modules(`*.module.css`) + `styles/variables.css`의 CSS 변수. 별도 CSS 라이브러리 없음.
- 이유: 팀 요청(공통 컴포넌트 중심 구성) + 기능 4개(content/script/editor/video)가 화면 흐름과 1:1로 대응해 찾기 쉽다.

### D-03. 라우팅: React Router 미도입
- 결정: 현재는 단일 페이지(`HomePage`)에서 단계 상태로 화면을 전환한다.
- 이유: 흐름이 한 방향 위저드이고 장면 편집 상태를 페이지 간에 넘길 필요가 없다. 공유 가능한 URL(예: `/jobs/:id`)이 필요해지면 도입한다.

### D-04. Backend: FastAPI + Pydantic + Uvicorn
- 결정: FastAPI 앱 팩토리(`create_app`) + 버전 라우터(`/api/v1`).
- 이유: Pydantic 스키마로 요청/응답 검증과 OpenAPI 문서(`/docs`)가 자동으로 나온다. OpenAI·FFmpeg를 쓰는 Python 생태계와 잘 맞는다.
- 반영한 공식 문서 내용:
  - [Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/): 기능별 `APIRouter` 모듈을 만들고 `include_router(prefix=...)`로 묶는다. 모듈 단위로 import해 `router` 이름 충돌을 피한다. 패키지마다 `__init__.py`.
  - [Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/): `BaseSettings` + `SettingsConfigDict(env_file=".env")`, `@lru_cache`로 감싼 `get_settings()`를 의존성으로 쓰고 테스트에서 `dependency_overrides`로 교체한다.
  - [CORS](https://fastapi.tiangolo.com/tutorial/cors/): `CORSMiddleware`에 허용 Origin을 명시한다. 쿠키를 쓰지 않으므로 `allow_credentials=False`.
  - [Testing](https://fastapi.tiangolo.com/tutorial/testing/): `TestClient` + pytest. 문서는 httpx 설치를 안내하지만, 설치된 Starlette가 `httpx` 대신 `httpx2`를 쓰라는 경고(`StarletteDeprecationWarning`)를 내서 개발 의존성은 `httpx2`로 두었다.

### D-05. Python 3.13 + uv
- 결정: Python 3.13으로 고정(`.python-version`, `requires-python = ">=3.13,<3.14"`), 패키지·가상환경은 uv로 관리(`uv.lock` 커밋).
- 이유: 팀 지정 버전. uv 하나로 인터프리터 설치·가상환경·의존성 잠금·실행(`uv run`)을 처리할 수 있다.

### D-06. 설정·비밀 관리
- 결정: 백엔드 `pydantic-settings`, `.env`는 Git 제외, `.env.example`만 커밋. `OPENAI_API_KEY`는 `SecretStr`.
- 반영한 공식 문서 내용 ([Pydantic Settings](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/)): 실제 환경변수가 `.env`보다 우선한다. 리스트 같은 복합 타입은 JSON 문자열로 넣는다 → `CORS_ORIGINS=["http://localhost:5173"]`. `extra="ignore"`로 알 수 없는 `.env` 항목을 무시한다.
- 개발/프로덕션 분리: `APP_ENV`(development | production) 값과 환경변수로만 구분한다. 프로덕션은 배포 환경의 환경변수를 사용하고 `.env` 파일에 의존하지 않는다.

### D-07. 데이터베이스 미도입
- 결정: MVP에서는 DB를 쓰지 않는다. 장면 편집 상태는 프론트엔드, Job 상태는 백엔드 메모리, 산출물은 로컬 파일.
- 이유: 로그인·작업 내역 저장(OPT-04)이 범위 밖이라 영속 데이터가 없다.

### D-08. 장기 작업: FastAPI BackgroundTasks + 인메모리 Job
- 결정: `POST /videos`가 `202`와 `job_id`를 바로 반환하고, 렌더는 `BackgroundTasks`로 실행한다. 프론트엔드는 상태 API를 폴링한다.
- 반영한 공식 문서 내용 ([Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)): 백그라운드 작업은 응답을 보낸 뒤 같은 프로세스에서 실행된다. 여러 프로세스·서버로 분산해야 하는 무거운 작업에는 Celery 같은 도구(RabbitMQ/Redis 필요)를 권장한다.
- 이유: 단일 사용자 데모 규모라 동시 렌더가 적고, FFmpeg는 별도 프로세스로 실행되어 CPU 부담이 API 프로세스 밖에 있다. 렌더 함수는 동기 `def`로 작성해 스레드풀에서 실행되게 한다.
- 한계(수용): 서버 재시작 시 진행 중 작업·상태 유실, Uvicorn 워커 1개 전제. 동시 렌더 수는 세마포어로 1~2개로 제한.

### D-09. 영상 합성: FFmpeg CLI를 subprocess로 직접 호출
- 결정: `subprocess.run([...], check=True, timeout=...)`로 `ffmpeg`/`ffprobe`를 인자 배열로 호출한다. Python 래퍼 라이브러리(ffmpeg-python, MoviePy)는 쓰지 않는다.
- 이유: 필요한 기능(scale/pad, overlay, concat, 인코딩)이 단순하고, 래퍼 없이도 명령이 명확하며 의존성이 줄어든다.
- 자막: `subtitles`/`drawtext` 필터 대신 자막을 PNG로 그려 `overlay`한다. 로컬 FFmpeg 9.0.2(Homebrew) 빌드에 libass·freetype이 없어 두 필터가 없음을 `ffmpeg -filters`로 확인했다. PNG 방식은 FFmpeg 빌드 옵션에 덜 의존하고 한글 폰트 처리가 쉽다 (Pillow는 5단계에서 추가).
- 출력: 1080×1920, H.264(libx264, 로컬 빌드 포함 확인) + AAC, MP4.

### D-10. OpenAI 연동 방식
- 대본: Responses API의 Structured Outputs(`client.responses.parse(..., text_format=PydanticModel)`)로 스키마를 강제하고, 거절(`refusal`)·불완전(`status="incomplete"`) 응답을 오류로 처리한다. 장면 수·역할 순서 규칙은 Pydantic validator로 한 번 더 검사한다. ([Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs))
- TTS: `gpt-4o-mini-tts` 우선. `tts-1`/`tts-1-hd`는 2027-01-06 종료 예정이라 쓰지 않는다. AI 생성 음성임을 사용자에게 고지해야 한다. ([Text to speech](https://developers.openai.com/api/docs/guides/text-to-speech))
- 모델명·음성은 설정값으로 둔다.

### D-11. 파일 저장 전략
- 결정: `backend/storage/`(설정 `STORAGE_DIR`) 아래 `assets/`, `jobs/{job_id}/`. 파일명은 서버 생성 UUID. TTL(기본 24시간) 지난 파일 삭제.
- 이유: 단일 서버 데모에 충분하고 구현이 가장 단순하다.

### D-12. 추가 도구 미도입
- 미도입: React Router, 상태관리 라이브러리(Redux 등), CSS 프레임워크, Vitest, ruff, Docker, Celery/Redis.
- 이유: 현재 스켈레톤에 필요가 없다. 각각 필요해지는 단계(development-plan.md)에서 이유와 함께 다시 결정한다.

## 추후 검토 사항

| 항목 | 검토 시점 | 메모 |
|---|---|---|
| 프론트엔드 테스트 도구(Vitest) | 4단계 | 장면 상태 reducer 테스트가 생기면 도입 |
| Python 린터/포매터(ruff) | 2단계 | 서비스 코드가 늘어나면 도입 |
| HTML 파서·HTTP 클라이언트 | 2단계 | beautifulsoup4 + httpx 예정 |
| 한글 폰트 선택·라이선스 | 5단계 | OFL 라이선스 폰트(예: Noto Sans KR) 후보 |
| 작업 큐(Celery/RQ 등) | 배포 시 | 다중 사용자·다중 워커가 필요해질 때만 |
| 오브젝트 스토리지 | 배포 시 | 컨테이너 디스크 휘발 문제 대응 |
| Docker 이미지 | 8단계 | FFmpeg 포함 이미지로 실행 환경 고정 |
| 배포 구성 | 8단계 | 백엔드가 프론트엔드 정적 파일까지 제공하는 단일 서버 구성 우선 검토 |
