# features/editor — ③ 장면 확인·수정 (FR-03)

- `EditorWorkspace.tsx`: [편집 | 원문] 탭. 편집 탭은 장면, 음성·음악. "영상 제작" 버튼은 아래 고정 막대(`features/pipeline/ProgressDock.tsx`)에 있음
- `SceneList.tsx`: 편집 탭의 장면 영역. 훅 문구, 자막 카드 목록, 장면 추가(CTA 앞 점선 카드)
- `SceneStrip.tsx`: 자막 카드를 가로로 늘어놓은 목록. 마우스로 카드 빈 곳이나 썸네일을 잡고 끌면 좌우로 넘김(조금이라도 끌면 클릭으로 치지 않음)
- `SubtitleCard.tsx`: 자막 하나를 카드 하나로 표시. 같은 장면의 카드는 이미지를 같이 쓰고 `1/3`처럼 순서를 표시. 움직임은 장면 첫 카드에서만 고치고, 나머지 카드는 같은 높이의 빈 자리로 둬서 카드 높이를 맞춤. 화면 제목(`caption`)은 영상에 쓰이지 않아 화면에서 뺐음(서버에는 비어 있으면 내레이션 앞부분을 보냄). 중간 카드에서 이미지를 바꾸면 그 자막부터 새 장면이 되고, 앞뒤 장면과 이미지가 같아지면 다시 합쳐짐(`pipelineReducer.ts`의 `setSceneImage`)
- `SceneMenu.tsx`: 카드 머리의 ⋮ 메뉴 — 원문 위치 보기, 이 자막 삭제, 장면 삭제. 화살표·Home·End·Esc로 조작
- `ImagePicker.tsx`: 블로그 이미지 / 내 컴퓨터 이미지(브라우저 임시 주소) / 이미지 없음 선택
- 장면 상태는 서버에 저장하지 않고 `features/pipeline/pipelineReducer.ts`에서 관리 (docs/architecture.md 2절)
