# 디자인 시스템 — Blog to Shorts

> v0.2 (2026-11-03) · 프론트엔드 화면은 이 문서의 토큰과 공통 컴포넌트만으로 만든다.
> 구현 위치: 토큰 `frontend/src/styles/variables.css`, 컴포넌트 `frontend/src/components/common/`, 레이아웃 `frontend/src/components/layout/`

## 1. 기준과 원칙

- **기준**: 팀 데모 화면(`smartdong-demo/static/index.html`)의 톤을 따른다. 따뜻한 회백색 배경, 흰 카드, 네이버 그린 강조색, 검정 활성 탭, 단계 카드.
- **정보 우선**: 장식(그림자·그라데이션·일러스트)을 쓰지 않는다. 구분은 테두리(`line`)와 배경 차이로만 한다.
- **강조색은 하나**: 그린(`accent`)은 주요 행동(버튼), 완료·성공 상태에만 쓴다.
- **상태는 색 + 글자/기호**: 색만으로 상태를 구분하지 않는다(✓, 스피너, "실패" 등 함께 표시).

## 2. 디자인 토큰

CSS 변수로 정의한다. 컴포넌트 CSS만 토큰을 직접 참조하고, 페이지·feature 코드는 컴포넌트 props로만 표현한다.

### 2.1 색

| 토큰 | 값 | 용도 |
|---|---|---|
| `--color-bg` | `#f6f5f1` | 페이지 배경 |
| `--color-surface` | `#ffffff` | 카드·입력 배경 |
| `--color-subtle` | `#f0efea` | 보조 버튼, 비활성 탭, 회색 배지 배경 |
| `--color-text` | `#1d1d1f` | 본문 글자, 활성 탭 배경 |
| `--color-text-muted` | `#8a8a8e` | 보조 설명, 캡션, 플레이스홀더 |
| `--color-text-soft` | `#555555` | 요약 등 본문보다 약한 문단 |
| `--color-line` | `#e4e2dc` | 카드·입력 테두리, 구분선 |
| `--color-accent` | `#03c75a` | 주요 버튼, 성공·완료, CTA 역할 |
| `--color-accent-bg` | `#eefaf3` | 완료 상태 배경 |
| `--color-accent-line` | `#bfe8cf` | 완료 상태 테두리 |
| `--color-danger` | `#e5484d` | 오류, 중지 버튼, HOOK 역할 |
| `--color-danger-bg` | `#fdeeee` | 오류 상태 배경 |
| `--color-danger-line` | `#f3c0c1` | 오류 상태 테두리 |
| `--color-warn` | `#c77a03` | 경고(예: 예상 길이 범위 밖) |
| `--color-info` | `#5b5bd6` | 본문(BODY) 역할, 정보성 링크 |
| `--color-media-placeholder` | `#22224a` | 이미지 없는 썸네일 배경 |
| `--color-video` | `#000000` | 영상 영역 배경 |
| `--color-overlay` | `rgb(0 0 0 / 55%)` | 이미지 위 글자 띠·라벨 배경 |
| `--color-backdrop` | `rgb(0 0 0 / 40%)` | 모달 뒤 배경 |

### 2.2 타이포그래피

글꼴: `-apple-system, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif` / 숫자 표시는 `font-variant-numeric: tabular-nums`

| 토큰 | 크기 / 굵기 | 용도 (`Text` variant) |
|---|---|---|
| `--font-size-title` | 26px / 700 | 페이지 제목 (`title`) |
| `--font-size-heading` | 16px / 700 | 카드 제목 (`heading`) |
| `--font-size-body` | 15px / 400 | 입력·버튼·본문 (`body`) |
| `--font-size-small` | 14px / 400 | 보조 문단, 메타 정보 (`small`) |
| `--font-size-caption` | 12px / 400 | 캡션, 글자 수, 단계 메시지 (`caption`) |
| `--font-size-micro` | 11px / 700~800 | STEP 번호, 역할 배지 |

### 2.3 간격

| 토큰 | 값 | 주 용도 |
|---|---|---|
| `--space-4` | 4px | 아이콘·글자 사이 |
| `--space-6` | 6px | 탭 사이, 작은 묶음 |
| `--space-8` | 8px | 입력과 버튼 사이, 단계 카드 사이 |
| `--space-10` | 10px | 버튼·입력 안쪽 세로 여백 |
| `--space-12` | 12px | 카드 내부 요소 사이 |
| `--space-14` | 14px | 카드 사이 |
| `--space-18` | 18px | 카드 안쪽 여백 |
| `--space-20` | 20px | 섹션 사이, 페이지 좌우 여백 |
| `--space-40` | 40px | 페이지 상단 여백 |

`Stack`·`Grid`의 `gap` prop은 위 숫자(4·6·8·10·12·14·18·20·40)만 받는다.

### 2.4 모서리·레이아웃·모션

| 토큰 | 값 | 용도 |
|---|---|---|
| `--radius-sm` | 6px | 배지 |
| `--radius-md` | 8px | 썸네일 |
| `--radius-lg` | 10px | 버튼·입력·탭 |
| `--radius-xl` | 12px | 카드, 단계 카드 |
| `--layout-max-width` | 1280px | 본문 최대 너비 |
| 반응형 기준 | 900px 이하 | 다열 그리드 → 열 수 축소 |
| 스피너 | 0.8s linear 무한 회전 | 진행 중 표시 |
| 비활성 | opacity 0.4 | 비활성 버튼 |

## 3. 공통 컴포넌트

모든 컴포넌트는 `components/common/<이름>/<이름>.tsx + <이름>.module.css + index.ts` 구조다. import는 폴더(`index.ts`) 경로로 한다: `import { Button } from '../components/common/Button'`.

### PageLayout (`components/layout/PageLayout`)
- 용도: 모든 페이지의 바깥 틀. 페이지 제목·부제 + 본문 세로 배치
- props: `title: string`, `description?: string`, `children`
- 규칙: 페이지마다 한 번만 쓴다. 본문은 카드 사이 간격 14px로 세로 배치된다.

### Stack
- 용도: 요소를 세로/가로로 간격 맞춰 배치 (페이지에서 CSS를 쓰지 않기 위한 배치 도구)
- props: `direction?: 'column' | 'row'`(기본 column), `gap?: 4|6|8|10|12|14|18|20|40`(기본 12), `align?: 'start'|'center'|'end'|'stretch'|'baseline'`, `justify?: 'start'|'center'|'end'|'between'`, `wrap?: boolean` (가로 배치에서 입력칸을 남은 너비로 늘릴 때는 `TextField`의 `grow` 사용)
- 예: `<Stack direction="row" gap={8} align="center">…</Stack>`

### Grid
- 용도: 같은 크기 칸을 여러 열로 배치 (STEP 카드, 이미지 선택 목록)
- props: `columns: number`, `compactColumns?: number`(900px 이하 열 수, 기본 2), `gap?`(Stack과 동일, 기본 8)

### Text
- 용도: 모든 글자 표현. 페이지에서 `<p style>`·CSS 클래스 대신 사용
- props: `variant?: 'title'|'heading'|'body'|'small'|'caption'`(기본 body), `tone?: 'default'|'muted'|'soft'|'accent'|'danger'|'warn'`(기본 default), `as?: 'p'|'span'|'h1'|'h2'|'h3'|'div'`
- 규칙: `title`은 PageLayout 안에서만 쓰인다(직접 쓰지 않음). 카드 제목은 `Card`의 `title`을 쓴다.

### Button
- 용도: 모든 클릭 행동
- props: `variant?: 'primary'|'ghost'|'icon'|'danger'`(기본 primary), `loading?`, `disabled?`, 기본 `<button>` 속성
- variant
  | variant | 모양 | 쓰는 곳 |
  |---|---|---|
  | `primary` | 그린 배경, 흰 글자 600 | 화면당 핵심 행동 1개 (분석하기, 영상 만들기) |
  | `ghost` | 회색(`subtle`) 배경, 검정 글자 500 | 보조 행동 (다시 확인, 원문 보기, 장면 추가) |
  | `icon` | 작은 회색 버튼 | ↑ ↓ 삭제 같은 아이콘 동작 |
  | `danger` | 빨강 배경 | 중지하기 |
- 규칙: 한 카드 안에 `primary`는 하나만. `loading` 중에는 자동 비활성.

### Card
- 용도: 화면의 구역(섹션). 데모의 `section`
- props: `title?: string`, `actions?: ReactNode`(제목 오른쪽 버튼 영역), `id?`(스크롤 이동 대상), `children`
- 모양: 흰 배경, 1px `line` 테두리, radius 12, 안쪽 여백 18, 제목 16px/700

### Tabs
- 용도: 같은 자리에서 입력 방식 전환 (블로그 URL / 본문 붙여넣기)
- props: `items: { value: string; label: string }[]`, `value: string`, `onChange(value)`, `ariaLabel: string`
- 모양: 회색 버튼 나열, 선택된 탭은 검정 배경·흰 글자
- 규칙: 제어형으로만 쓴다(상태는 부모가 가짐). 키보드 ←/→로 이동.

### TextField
- 용도: 한 줄 입력 / 여러 줄 입력
- props: `label?`(화면 표시), `ariaLabel?`(label 없을 때 필수), `multiline?`, `rows?`(주면 그 줄 수, 없으면 최소 높이 160px), `grow?`(가로 Stack에서 남은 너비 차지), `hint?`(아래 회색 안내), `error?`(아래 빨간 오류, 테두리 빨강), 기본 input/textarea 속성
- 모양: 흰 배경, 1px `line`, radius 10, 15px, 안쪽 10×12

### StepCard
- 용도: 처리 단계 진행 표시 (STEP 1~5: 컨텐츠 가져오기 · 대본 구상하기 · 장면 · 음성과 음악 · 영상 제작)
- props: `step: number`, `title: string`, `message: string`, `status: StepStatus`, `meta?: string`(소요 시간·비용 줄)
- 상태 표현
  | status | 배경 / 테두리 | 표시 |
  |---|---|---|
  | `idle` | 흰색 / `line` | 메시지 회색 |
  | `running` | 흰색 / `accent` | STEP 번호 옆 그린 스피너 |
  | `waiting` | 흰색 / `text` 2px | 메시지 검정 600 — 사용자 확인을 기다리는 단계 (검토 모드의 STEP 4) |
  | `done` | `accent-bg` / `accent-line` | STEP 번호 옆 ✓ |
  | `error` | `danger-bg` / `danger-line` | 메시지 빨강 |
  | `cancelled` | `subtle` / `line` | 메시지 회색 |

### RoleBadge
- 용도: 장면 역할 표시
- props: `role: 'hook'|'body'|'cta'`, `index?: number`("#1 HOOK"처럼 앞에 번호)
- 색: HOOK `danger`, 본문 `info`, CTA `accent` — 흰 글자 11px/800, radius 6

### StatusBadge
- 용도: 연결·작업 상태를 알약 모양으로 표시
- props: `tone: 'success'|'danger'|'neutral'`, `label: string`

### SegmentedControl
- 용도: 둘 이상 중 하나 고르기 (진행 방식: 장면 확인 후 만들기 / 처음부터 끝까지 자동)
- props: `items: { value; label }[]`, `value`, `onChange(value)`, `ariaLabel`, `disabled?`
- 모양: 회색 트랙 안에 붙은 버튼, 선택 항목은 검정 배경·흰 글자. 따로 떨어진 `Tabs`와 구분된다
- 규칙: `role="radiogroup"`/`role="radio"`, 키보드 ←/→ 이동. 진행 중에는 `disabled`

### Select
- 용도: 목록에서 하나 고르기 (장면 움직임, 목소리, 배경음악)
- props: `options: { value; label }[]`, `label?`, `ariaLabel?`(label 없을 때 필수), 기본 select 속성
- 모양: `TextField`와 같은 테두리·크기

### Range
- 용도: 숫자 값 슬라이더 (음악 크기)
- props: `label`, `value: number`, `unit?`(예: `%`), 기본 range input 속성(min·max·step 등)
- 모양: 라벨 왼쪽, 현재 값 오른쪽(tabular-nums), 슬라이더 색은 `text`

### SceneThumb
- 용도: 장면 이미지 썸네일 + 이미지 변경 버튼
- props: `src: string | null`, `label?`(기본 "이미지 변경"), `onClick?`, `disabled?`
- 모양: 9:16, 가로 120px, radius 8. 이미지 없으면 `media-placeholder` 배경에 "이미지 없음", 하단 `overlay` 띠

### Dialog
- 용도: 모달 (장면 이미지 선택)
- props: `open`, `title`, `onClose`, `footer?`, `children`
- 규칙: `<dialog>` + `showModal()`. Esc·바깥 클릭으로 닫힌다. 브라우저 `alert/confirm`은 쓰지 않는다

### Toast
- 용도: 실패 원인 알림 (API 키 만료 등)
- 구성: `ToastList`(`toasts`, `onDismiss`) + `hooks/useToast`
- 규칙: 오른쪽 위 고정, `--color-danger*` 색, `role="alert"`. 안내를 읽어야 하므로 자동으로 사라지지 않고 X 또는 새 실행 시작으로 닫힌다. 같은 문구는 쌓지 않는다

### VideoPlayer
- 용도: 9:16 세로 영상 자리
- props: `src: string | null`, `label`(스크린리더용)
- 모양: 가로 300px(좁으면 100%), radius 12, `video` 배경. `src`가 없으면 검은 화면만 (백엔드 연결 전)

### SplitLayout (`components/layout/SplitLayout`)
- 용도: [보조 패널 | 본문] 2열 (원문 | 장면 확인)
- props: `aside`, `asideVisible`, `children`
- 모양: 1 : 1.35 비율, 보조 패널은 화면에 붙어 따라오며(sticky) 따로 스크롤. 900px 이하에서는 위아래로 쌓인다

## 4. 사용 규칙

1. `pages/`·`features/` 코드에는 **색 값(hex)·px·인라인 style을 쓰지 않는다.** 필요한 표현은 컴포넌트 props로 한다.
2. `pages/`에는 `.module.css`를 만들지 않는다. 배치는 `PageLayout`·`Stack`·`Grid`·`Card`로 한다.
3. `features/<기능>/`에 그 기능 전용 컴포넌트를 만들 때도 공통 컴포넌트를 조합한다. 전용 스타일이 꼭 필요하면 해당 컴포넌트 옆 `.module.css`에서 **토큰만** 사용한다.
4. 같은 UI 패턴이 두 기능 이상에서 나오면 `components/common`으로 옮기고 이 문서 3절에 명세를 추가한다.
5. 새 색·크기가 필요하면 먼저 2절에 토큰을 추가한 뒤 쓴다.
6. 접근성: 버튼은 `<button>`, 입력에는 label 또는 `ariaLabel`, 탭은 `role="tablist"`/`aria-selected`, 상태 배지는 `role="status"`.

## 5. 화면 구성 (`pages/HomePage.tsx`)

```
PageLayout  "블로그 → 숏폼 영상" + 부제
├── Card         입력: Tabs(블로그 URL | 본문 붙여넣기) + TextField + Button(primary)
│                진행 방식 SegmentedControl(장면 확인 후 만들기 | 처음부터 끝까지 자동) + 안내 문구
├── RenderStatus 지금 하는 일·경과 시간 + Button(danger "중지하기")
├── Grid(5)      StepCard × 5  컨텐츠 가져오기 · 대본 구상하기 · 장면 · 음성과 음악 · 영상 제작
├── SplitLayout  [가져온 컨텐츠(원문·이미지) | 장면 확인]
│                장면 확인 = 대본 요약 + SceneCard × 4~6 + 음성과 음악(Select·Range) + Button(primary "영상 만들기")
├── Card         완성 영상: VideoPlayer(검은 9:16) + 요약 + 장면 다시 수정하기
└── Card         백엔드 연결 상태 (개발 확인용)
```

진행 방식

| 방식 | 흐름 | 시작 버튼 |
|---|---|---|
| 장면 확인 후 만들기 (기본) | 1~3단계 → 멈춤(STEP 4 `waiting`) → 장면·음성 확인 → "영상 만들기" → 4~5단계 | 장면까지 만들기 |
| 처음부터 끝까지 자동 | 1~5단계를 멈추지 않고 진행. 완성 후 장면을 고쳐 "영상 다시 만들기"(4~5단계만) | 영상까지 만들기 |

## 6. 추가 예정 컴포넌트

해당 기능 단계에서 이 문서에 명세를 먼저 쓰고 구현한다.

| 컴포넌트 | 단계 | 내용 |
|---|---|---|
| `LogItem` | 선택 | 단계별 요청·결과 로그 한 줄 + 펼치기 |
