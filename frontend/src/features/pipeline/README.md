# features/pipeline — 5단계 진행 상태와 목업 API

화면의 ① 컨텐츠 가져오기 → ② 대본 구상하기 → ③ 장면 → ④ 음성과 음악 → ⑤ 영상 제작 흐름을 관리한다.

| 파일 | 역할 |
|---|---|
| `types.ts` | 진행 방식(`Mode`), 단계 상태, Content·Scene·AudioSettings 등. 필드 이름은 docs/api-design.md 응답에 맞춤 |
| `pipelineReducer.ts` | `useReducer` 상태와 액션 (단계 시작·완료·실패·중지, 장면 편집, 음성 설정) |
| `usePipeline.ts` | 단계 실행 순서. `start()`는 ①부터, `render()`는 ④~⑤만. 중지는 `AbortController`. 실패는 `onError`로 알리고(토스트), 영상 작업 실패는 2초 간격 상태 조회로 감지 |
| `scenes.ts` | 장면 규칙(4~6개, HOOK·본문·CTA 역할), 예상 길이 계산 |
| `mockApi.ts` | **백엔드 연결 전 가짜 응답.** 실제 API를 붙일 때 이 파일의 함수 본문만 fetch 호출로 바꾼다 |
| `mockData.ts` | 예시 글·요약·장면 (이미지는 `public/mock/*.svg`) |

진행 방식

- `review`(장면 확인 후 만들기): ①~③ 후 `phase = 'review'`로 멈추고 STEP 4를 `waiting`으로 표시
- `auto`(처음부터 끝까지 자동): ①~⑤를 이어서 실행
- 완성 후 장면·음성 설정을 바꾸면 `stale = true` → "영상 다시 만들기"로 ④~⑤만 다시 실행
