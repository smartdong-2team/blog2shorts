# features/video — ⑤ 영상 제작·결과 확인 (FR-05~06)

- `RenderStatus.tsx`: 단계 카드 위 한 줄 — 지금 하는 일·경과 시간, 진행 중이면 "중지하기"
- `VideoPreview.tsx`: 완성 영상 카드. 백엔드 연결 전에는 검은 9:16 화면 + 길이·장면 흐름·목소리/음악 요약, mp4 다운로드는 비활성
- 데이터는 현재 `features/pipeline/mockApi.ts`의 `renderVideo` (실제: `POST /api/v1/videos` → `GET /api/v1/videos/{job_id}` 폴링)
