# 디자인 시스템 — Blog to Shorts

> v0.1 (2026-11-03) · 프론트엔드 화면은 이 문서의 토큰과 공통 컴포넌트만으로 만든다.
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
- props: `title?: string`, `actions?: ReactNode`(제목 오른쪽 버튼 영역), `children`
- 모양: 흰 배경, 1px `line` 테두리, radius 12, 안쪽 여백 18, 제목 16px/700

### Tabs
- 용도: 같은 자리에서 입력 방식 전환 (블로그 URL / 본문 붙여넣기)
- props: `items: { value: string; label: string }[]`, `value: string`, `onChange(value)`, `ariaLabel: string`
- 모양: 회색 버튼 나열, 선택된 탭은 검정 배경·흰 글자
- 규칙: 제어형으로만 쓴다(상태는 부모가 가짐). 키보드 ←/→로 이동.

### TextField
- 용도: 한 줄 입력 / 여러 줄 입력
- props: `label?`(화면 표시), `ariaLabel?`(label 없을 때 필수), `multiline?`, `rows?`, `grow?`(가로 Stack에서 남은 너비 차지), `hint?`(아래 회색 안내), `error?`(아래 빨간 오류, 테두리 빨강), 기본 input/textarea 속성
- 모양: 흰 배경, 1px `line`, radius 10, 15px, 안쪽 10×12

### StepCard
- 용도: 처리 단계 진행 표시 (STEP 1~5)
- props: `step: number`, `title: string`, `message: string`, `status: StepStatus`, `meta?: string`(소요 시간·비용 줄)
- 상태 표현
  | status | 배경 / 테두리 | 표시 |
  |---|---|---|
  | `idle` | 흰색 / `line` | 메시지 회색 |
  | `running` | 흰색 / `accent` | STEP 번호 옆 그린 스피너 |
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

## 4. 사용 규칙

1. `pages/`·`features/` 코드에는 **색 값(hex)·px·인라인 style을 쓰지 않는다.** 필요한 표현은 컴포넌트 props로 한다.
2. `pages/`에는 `.module.css`를 만들지 않는다. 배치는 `PageLayout`·`Stack`·`Grid`·`Card`로 한다.
3. `features/<기능>/`에 그 기능 전용 컴포넌트를 만들 때도 공통 컴포넌트를 조합한다. 전용 스타일이 꼭 필요하면 해당 컴포넌트 옆 `.module.css`에서 **토큰만** 사용한다.
4. 같은 UI 패턴이 두 기능 이상에서 나오면 `components/common`으로 옮기고 이 문서 3절에 명세를 추가한다.
5. 새 색·크기가 필요하면 먼저 2절에 토큰을 추가한 뒤 쓴다.
6. 접근성: 버튼은 `<button>`, 입력에는 label 또는 `ariaLabel`, 탭은 `role="tablist"`/`aria-selected`, 상태 배지는 `role="status"`.

## 5. 화면 구성 (데모 기준 배치)

```
PageLayout  "블로그 → 숏폼 영상" + 부제
├── Card      입력: Tabs(블로그 URL | 본문 붙여넣기) + TextField + Button(primary "분석하기")
├── Grid(5)   StepCard × 5  글 읽기 · 이미지 수집 · 대본 작성 · 음성(TTS) · 영상 합성
├── Card      장면 편집: [원문 | 장면 목록] (RoleBadge, SceneThumb, TextField)   ← 4단계에서 구현
├── Card      완성 영상: VideoPlayer + 다운로드                                ← 7단계에서 구현
└── Card      백엔드 연결 상태 (개발 확인용)
```

## 6. 추가 예정 컴포넌트

해당 기능 단계에서 이 문서에 명세를 먼저 쓰고 구현한다.

| 컴포넌트 | 단계 | 내용 |
|---|---|---|
| `SceneThumb` | 4 | 9:16 썸네일(가로 120px), 이미지 없으면 `media-placeholder` 배경, 하단 "이미지 변경" 띠 |
| `Dialog` | 4 | 이미지 선택 모달 (`<dialog>` 기반) |
| `VideoPlayer` | 7 | 9:16 비디오(가로 300px), 검정 배경, radius 12 |
| `LogItem` | 선택 | 단계별 요청·결과 로그 한 줄 + 펼치기 |
