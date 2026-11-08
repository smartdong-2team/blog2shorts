// 영상의 제목 배치(backend layout_hook)와 같은 규칙으로 미리보기 제목을 배치한다.
// 브라우저 글꼴로 재므로 실제 영상과 약간 다를 수 있다.

const VIDEO_WIDTH = 1080
const MAX_WIDTH = 1000
const MAX_FONT_SIZE = 80
const MIN_FONT_SIZE = 44
const MEASURE_SIZE = 100
const SUBTITLE_FONT_SIZE = 60
const SUBTITLE_MAX_WIDTH = 960
const MIN_SUBTITLE_FONT_SIZE = 32

let context: CanvasRenderingContext2D | null = null

function widthPerPx(text: string) {
  context ??= document.createElement('canvas').getContext('2d')
  if (!context) return text.length

  context.font = `800 ${MEASURE_SIZE}px sans-serif`
  return context.measureText(text).width / MEASURE_SIZE
}

function balance(text: string) {
  const words = text.split(/\s+/)

  if (words.length === 1 || widthPerPx(text) * MAX_FONT_SIZE <= MAX_WIDTH) return [text]

  let best = [text]
  let bestGap = Infinity

  for (let i = 1; i < words.length; i++) {
    const first = words.slice(0, i).join(' ')
    const second = words.slice(i).join(' ')
    const gap = Math.abs(widthPerPx(first) - widthPerPx(second))

    if (gap < bestGap) {
      best = [first, second]
      bestGap = gap
    }
  }

  return best
}

/** 자막의 줄은 그대로 두고, 영상처럼 폭에 맞춘 글자 크기(cqw)를 돌려준다 */
export function subtitleFontSize(text: string) {
  const widest = Math.max(...text.split(/\r?\n/).map(widthPerPx), 0)
  const size = widest > 0 ? Math.min(SUBTITLE_FONT_SIZE, SUBTITLE_MAX_WIDTH / widest) : SUBTITLE_FONT_SIZE

  return `${(Math.max(MIN_SUBTITLE_FONT_SIZE, size) / VIDEO_WIDTH) * 100}cqw`
}

/** 제목을 최대 두 줄로 나누고, 썸네일 폭 기준 글자 크기(cqw)를 돌려준다 */
export function layoutHook(text: string) {
  const rows = text
    .split(/\r?\n/)
    .map((row) => row.trim())
    .filter(Boolean)

  if (!rows.length) return { text: '', fontSize: '0cqw' }

  const lines = rows.length > 1 ? [rows[0], rows.slice(1).join(' ')] : balance(rows[0])
  const widest = Math.max(...lines.map(widthPerPx))
  const size = Math.max(MIN_FONT_SIZE, Math.min(MAX_FONT_SIZE, MAX_WIDTH / widest))

  return { text: lines.join('\n'), fontSize: `${(size / VIDEO_WIDTH) * 100}cqw` }
}
