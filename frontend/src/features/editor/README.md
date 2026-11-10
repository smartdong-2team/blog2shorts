# features/editor — ③ 장면 확인·수정 (FR-03)

- `SceneList.tsx`: 장면 확인 카드. 대본 요약, 예상 길이(목표 30~60초), 장면 목록, 장면 추가, 음성과 음악 설정, "영상 만들기" 버튼
- `SceneCarousel.tsx`: 장면 카드를 가로로 넘겨 보는 목록. 좌우 버튼, 빈 곳 끌기(마우스), 현재 위치(`2~5 / 6 장면`)와 점 표시
- `SceneCard.tsx`: 장면 한 개 — 역할 배지, 움직임, 썸네일(누르면 이미지 변경), 화면 제목, 자막 편집(자막을 이어 붙인 내용이 나레이션, 줄마다 ✕로 삭제)
- `SceneMenu.tsx`: 장면 머리의 ⋮ 메뉴 — 원문 위치 보기, 선택한 자막부터 장면 나누기, 앞 장면과 합치기, 앞뒤 이동, 장면 삭제. 화살표·Home·End·Esc로 조작
- `ImagePicker.tsx`: 블로그 이미지 / 내 컴퓨터 이미지(브라우저 임시 주소) / 이미지 없음 선택
- 장면 상태는 서버에 저장하지 않고 `features/pipeline/pipelineReducer.ts`에서 관리 (docs/architecture.md 2절)
