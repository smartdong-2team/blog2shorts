# features/editor — ③ 장면 확인·수정 (FR-03)

- `SceneList.tsx`: 장면 확인 카드. 대본 요약, 예상 길이(목표 30~60초), 장면 목록, 장면 추가, 음성과 음악 설정, "영상 만들기" 버튼
- `SceneCard.tsx`: 장면 한 개 — 썸네일(누르면 이미지 변경), 역할 배지, 화면 제목, 움직임, 나레이션, ↑↓·삭제·원문 위치 보기
- `ImagePicker.tsx`: 블로그 이미지 / 내 컴퓨터 이미지(브라우저 임시 주소) / 이미지 없음 선택
- 장면 상태는 서버에 저장하지 않고 `features/pipeline/pipelineReducer.ts`에서 관리 (docs/architecture.md 2절)
