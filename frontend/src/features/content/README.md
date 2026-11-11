# features/content — ① 컨텐츠 가져오기 (FR-01)

- `ContentInputForm.tsx`: 블로그 URL / 본문 붙여넣기 탭, 1차 검증(네이버 블로그 글 주소, 본문 200자 이상), **진행 방식 토글**, 시작 버튼(방식에 따라 "장면까지 만들기" / "영상까지 만들기")
- `ExtractResult.tsx`: 가져온 원문. 제목 아래 본문 속 `[이미지 N]` 자리에 이미지를 넣어 블로그 순서대로 보여 주고, 이미지마다 쓰인 장면 번호 표시(안 쓰인 이미지는 흐리게). `[이미지 N]` 자리는 백엔드 추출 API가 블로그 본문의 이미지 위치에 넣어 준다(대본 요청 때는 빼고 보냄)
- 데이터는 현재 `features/pipeline/mockApi.ts`의 `extractContent` (실제: `POST /api/v1/content/extract`)
