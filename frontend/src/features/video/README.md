# features/video — 영상 생성·결과 확인 (FR-04~06)

> 아직 구현되지 않음. 개발 계획 6~7단계에서 작성한다.

- `POST /api/v1/videos`로 렌더 시작, `GET /api/v1/videos/{job_id}` 폴링
- `<video>` 미리보기, 다운로드, 실패 시 재시도, AI 생성 음성 고지
- 예정 파일: `RenderPanel.tsx`, `VideoPreview.tsx`, `useRenderJob.ts`, `api.ts`
