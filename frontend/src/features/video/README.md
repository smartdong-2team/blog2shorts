# features/video — ⑤ 영상 제작·결과 확인 (FR-05~06)

- 진행 상황 한 줄과 "중지하기"는 아래 고정 막대로 옮겼다 (`features/pipeline/ProgressDock.tsx`)
- `VideoPreview.tsx`: 완성 영상 카드. 백엔드 연결 전에는 검은 9:16 화면 + 길이·장면 흐름·목소리/음악 요약, mp4 다운로드는 비활성
- `fileName.ts`: 다운로드 기본 이름 `MMDD_HHmm_제목첫단어.mp4` (제목 없으면 `blog2shorts`, 첫 단어는 20자까지)
- `useVideoDownload.ts`: 크롬·엣지는 저장 창(`showSaveFilePicker`)을 띄워 위치·이름을 고르고, 그 밖의 브라우저는 기본 이름으로 바로 받는다. 실패는 토스트
- 데이터는 현재 `features/pipeline/mockApi.ts`의 `renderVideo` (실제: `POST /api/v1/videos` → `GET /api/v1/videos/{job_id}` 폴링)
