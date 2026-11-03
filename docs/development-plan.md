# 개발 계획 — Blog to Shorts

> 상태: v0.1 (2026-11-03) · 체크박스는 실제로 끝난 항목만 체크한다.

진행 원칙: 단계마다 백엔드 API → 테스트 → 프론트엔드 화면 순으로 만들고, 완료 조건을 확인한 뒤 다음 단계로 넘어간다. 각 단계에서 필요한 라이브러리만 그때 추가한다.

## 1단계. 프로젝트 초기 설정 — 완료 (2026-11-03)

작업
- [x] 요구사항·아키텍처·API·기술 결정 문서 작성 (`docs/`)
- [x] Frontend 스켈레톤 (Vite React TS, 공통 컴포넌트, API 클라이언트)
- [x] Backend 스켈레톤 (FastAPI, 설정, CORS, `/api/v1/health`, 테스트)
- [x] 루트 `.gitignore`, `README.md`

완료 조건
- `npm run build`, `npm run lint`, `uv run pytest` 통과
- 브라우저 첫 화면에 백엔드 연결 상태가 "연결됨"으로 표시
- `/docs` Swagger UI 접근 가능, `.env`가 Git에 잡히지 않음

## 1.5단계. 프론트엔드 목업 흐름 — 완료 (2026-11-03)

백엔드 구현 전에 화면 흐름을 먼저 확정한다.

- [x] 5단계 화면(컨텐츠 가져오기 · 대본 구상하기 · 장면 · 음성과 음악 · 영상 제작)과 진행 방식 토글(장면 확인 후 만들기 / 처음부터 끝까지 자동)
- [x] 장면 편집(4단계 작업 중 프론트엔드 부분), 목소리·배경음악 선택, 중지
- [x] 목업 API(`frontend/src/features/pipeline/mockApi.ts`) — 2~7단계에서 실제 API로 하나씩 교체

## 2단계. 콘텐츠 입력 및 추출 (FR-01)

작업
- `services/content_extractor.py`: URL 파싱·allowlist 검증 → PostView URL 생성 → HTML 요청(리다이렉트 수동 검증) → 제목·본문·이미지 파싱
- 이미지 다운로드·검증·저장 (`storage/assets`), `GET /assets/{asset_id}`
- 공통 오류 포맷·예외 핸들러 (`{error:{code,message}}`)
- `POST /content/extract` 라우터·스키마
- 테스트: 예시 글 HTML을 픽스처로 저장해 파서 단위 테스트(네트워크 없이), URL 검증 케이스 표 테스트
- Frontend `features/content`: URL/본문 입력 탭, 1차 검증, 추출 결과(제목·본문 미리보기·이미지 썸네일)
- 추가 예정 라이브러리: `httpx`(런타임), `beautifulsoup4`, `Pillow`(이미지 검증)

완료 조건: requirements.md FR-01 AC 전부 충족

## 3단계. AI 대본 생성 (FR-02)

작업
- `schemas/script.py`: Scene/Script 모델 + 장면 규칙 validator
- `services/script_generator.py`: 프롬프트 작성, Responses API 구조화 출력, 거절·불완전 응답 처리, 1회 재시도
- `POST /scripts/generate`, 예상 길이 계산
- 테스트: OpenAI 호출을 가짜 클라이언트로 대체해 성공·스키마 위반·오류 케이스 검증
- Frontend `features/script`: 생성 버튼, 로딩, 결과 장면 목록
- 추가 예정 라이브러리: `openai`

완료 조건: FR-02 AC 충족, 예시 글로 실제 API 호출 1회 이상 성공 확인

## 4단계. 장면 편집 (FR-03)

작업
- Frontend `features/editor`: 장면 카드(역할·내레이션·자막·이미지), 문구 수정, 이미지 선택 모달, 대체 배경 미리보기
- 예상 길이 표시 및 30~60초 범위 경고
- 상태 관리: `useReducer` 기반 장면 상태 (외부 상태 라이브러리 없음)

완료 조건: FR-03 AC 충족, 수정 내용이 렌더 요청 페이로드에 반영됨(네트워크 탭 확인)

## 5단계. TTS 및 자막 (FR-04)

작업
- `services/tts.py`: 장면별 TTS 생성, `ffprobe`로 길이 측정
- `services/captions.py`: 자막 PNG 생성 (한글 폰트 파일 포함·라이선스 확인)
- 장면 길이 = 오디오 길이 + 여백 규칙 구현
- 테스트: TTS 가짜 구현 + 무음 오디오로 길이 계산 검증

완료 조건: 장면별 오디오·자막 이미지가 job 디렉터리에 생성되고 길이가 기록됨

## 6단계. 영상 합성 (FR-05)

작업
- `services/jobs.py`: 인메모리 Job 저장소, 상태 전이
- `services/video_renderer.py`: 장면 세그먼트(이미지 scale/pad 1080×1920 + 자막 overlay + 오디오) → concat → MP4(H.264/AAC)
- `POST /videos`(BackgroundTasks), `GET /videos/{job_id}`
- 실패 처리: 단계별 오류 코드, 중간 산출물 정리
- 테스트: 짧은 더미 장면 2개로 실제 FFmpeg 렌더 후 `ffprobe`로 해상도·길이·코덱 검증

완료 조건: FR-05 AC 충족, 60초 영상 합성 3분 이내(목표)

## 7단계. 미리보기 및 다운로드 (FR-06)

작업
- `GET /videos/{job_id}/download`(inline/attachment)
- Frontend `features/video`: 렌더 시작, 상태 폴링(1~2초), 진행 표시, `<video>` 미리보기, 다운로드, 실패·재시도, AI 음성 고지
- 파일 정리(TTL) 작업: 앱 시작 시 + 주기 실행

완료 조건: FR-06 AC 충족, 입력 → 다운로드 전 흐름을 예시 글로 끝까지 시연

## 8단계. 테스트 및 배포

작업
- 전체 흐름 수동 시나리오 테스트(URL 경로·직접 입력 경로·실패 경로)
- 백엔드 테스트 보강, 프론트엔드 핵심 로직 테스트(필요 시 Vitest 도입 검토)
- 배포 방식 결정: 단일 서버(백엔드가 빌드된 프론트엔드 정적 파일까지 제공) 또는 Docker 이미지(FFmpeg 포함)
- 프로덕션 설정 분리(`APP_ENV=production`, CORS Origin, 저장 경로, `/docs` 노출 여부)

완료 조건: 배포 URL에서 전체 흐름 동작, README에 배포·운영 방법 기록
