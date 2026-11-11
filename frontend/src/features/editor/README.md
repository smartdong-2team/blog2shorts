# features/editor — ③ 장면 확인·수정 (FR-03)

- `EditorWorkspace.tsx`: [편집 | 원문] 탭. 편집 탭은 장면, 음성·음악. "영상 제작" 버튼은 아래 고정 막대(`features/pipeline/ProgressDock.tsx`)에 있음
- `SceneList.tsx`: 편집 탭의 장면 영역. 훅 문구, 자막 카드 목록, 장면 추가(CTA 앞 점선 카드)
- `BulkEditor.tsx`: "전체 보기" 패널(장면 제목 옆 [카드 보기 | 전체 보기]로 전환). [전체 | 이미지 | 대본] 세 탭(전체는 이미지 아래 대본, 처음엔 전체), 고친 내용은 카드 보기와 똑같이 바로 반영. 이미지 순서는 장면·대본은 두고 이미지만 끌어다 놓기(사이 이미지는 한 칸씩 밀림) 또는 ←/→로 옮김. 대본은 한 칸에 전체 대본 — `──` 줄은 장면 구분, 빈 줄은 다음 자막, 줄바꿈은 자막 안 줄바꿈. 규칙에 어긋난 동안에는 마지막으로 맞았던 대본을 유지(변환은 `features/pipeline/scenes.ts`의 `scenesToScript`·`parseScript`·`applyScript`). 제작 중에는 보기만 가능
- `ScenePreparing.tsx`: 장면이 나오기 전(1~3단계) 자리. 단계마다 하는 일·결과·걸린 시간을 세로 진행 목록으로 보여 줌
- `SceneStrip.tsx`: 자막 카드를 가로로 늘어놓은 목록. 마우스로 카드 빈 곳이나 썸네일을 잡고 끌면 좌우로 넘김(조금이라도 끌면 클릭으로 치지 않음)
- `SubtitleCard.tsx`: 자막 하나를 카드 하나로 표시. 같은 장면의 카드는 이미지를 같이 쓰고 `1/3`처럼 순서를 표시. 움직임은 장면 첫 카드에서만 고치고, 나머지 카드는 같은 높이의 빈 자리로 둬서 카드 높이를 맞춤. 화면 제목(`caption`)은 영상에 쓰이지 않아 화면에서 뺐음(서버에는 비어 있으면 내레이션 앞부분을 보냄). 중간 카드에서 이미지를 바꾸면 그 자막부터 새 장면이 되고, 앞뒤 장면과 이미지가 같아지면 다시 합쳐짐(`pipelineReducer.ts`의 `setSceneImage`)
- `SceneMenu.tsx`: 카드 머리의 ⋮ 메뉴 — 원문 위치 보기, 이 자막 삭제, 장면 삭제. 화살표·Home·End·Esc로 조작
- `ImagePicker.tsx`: 블로그 이미지 / 내 컴퓨터 이미지(브라우저 임시 주소) / 이미지 없음 선택
- 장면 상태는 서버에 저장하지 않고 `features/pipeline/pipelineReducer.ts`에서 관리 (docs/architecture.md 2절)
