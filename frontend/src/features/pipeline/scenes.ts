import type { Motion, Scene } from './types'

export const MIN_SCENES = 4

// MAX_SCENES가 과연 꼭 필요할까? 일단은 6->30개로 만듦
export const MAX_SCENES = 30
export const TARGET_MIN_SEC = 30
export const TARGET_MAX_SEC = 60

export const MOTION_OPTIONS: { value: Motion; label: string }[] = [
  { value: 'zoom_in', label: '확대' },
  { value: 'zoom_out', label: '축소' },
  { value: 'pan_left', label: '왼쪽 이동' },
  { value: 'pan_right', label: '오른쪽 이동' },
]

let seq = 0
export const newSceneId = () => `scene-${Date.now().toString(36)}-${++seq}`

const chars = (s: string) => s.replace(/\s/g, '').length

/** 장면 한 개 나레이션 길이(초): 한국어 TTS 약 5.2자/초 */
export const narrationSec = (narration: string) => chars(narration) / 5.2

/** 전체 예상 길이(초): 말하는 시간 + 장면 여유 0.6초 − 전환 겹침 0.5초 (데모와 같은 공식) */
export function estimateSec(scenes: Scene[]) {
  const n = scenes.length
  if (n === 0) return 0
  const talk = scenes.reduce((sum, s) => sum + narrationSec(s.narration), 0)
  return talk + n * 0.6 - (n - 1) * 0.5
}

/** 장면의 자막 목록. 자막이 없는 장면은 나레이션 전체를 자막 하나로 본다 */
export const subtitlesOf = (scene: Scene) =>
  scene.subtitles?.length ? scene.subtitles : [scene.narration]

/** 나레이션은 자막을 순서대로 이어 붙인 것이다 */
export const narrationFromSubtitles = (subtitles: string[]) =>
  subtitles
    .map((text) => text.trim().replace(/\s+/g, ' '))
    .filter(Boolean)
    .join(' ')

/** 서버로 보내는 자막: 자막별 줄 목록 */
export const subtitlePagesOf = (scene: Scene) =>
  subtitlesOf(scene).map((text) => text.split(/\r?\n/).map((line) => line.trim()))

/** 영상을 만들 수 없는 자막이면 그 이유를 돌려준다 */
export function subtitleIssue(text: string) {
  if (!text.trim()) return '자막을 입력하거나 삭제해 주세요'

  const lines = text.split(/\r?\n/)
  if (lines.length > 2) return '자막 하나는 두 줄까지입니다. 자막을 추가해서 나눠 주세요'
  if (lines.some((line) => !line.trim())) return '빈 줄을 지워 주세요'

  return undefined
}

/** 첫 장면 HOOK, 마지막 CTA, 나머지 본문 */
export function assignRoles(scenes: Scene[]): Scene[] {
  return scenes.map((s, i) => ({ ...s, role: i === 0 ? 'hook' : i === scenes.length - 1 ? 'cta' : 'body' }))
}

/** 초 → "38초" / "1분 2초" */
export function formatSec(sec: number) {
  const s = Math.round(sec)
  return s >= 60 ? `${Math.floor(s / 60)}분 ${s % 60}초` : `${s}초`
}

/* ── 전체 보기: 대본 글 ↔ 장면 ──
 * "──"로 시작하는 줄 = 장면 구분, 빈 줄 = 다음 자막, 줄바꿈 = 자막 안 줄바꿈 */

const SCENE_LINE = /^\s*──/

/** 장면 → 한 칸짜리 대본 글 */
export function scenesToScript(scenes: Scene[]) {
  return scenes
    .map((scene, index) => [`── 장면 ${index + 1} ──`, subtitlesOf(scene).join('\n\n')].join('\n'))
    .join('\n\n')
}

/** 대본 글 → 장면별 자막 목록. 장면 구분 앞의 글은 첫 장면으로 본다 */
export function parseScript(text: string): string[][] {
  const blocks: string[][] = []
  let lines: string[] = []
  let started = false

  const flush = () => {
    if (!started && lines.every((line) => !line.trim())) return
    const subtitles = lines
      .join('\n')
      .split(/\n\s*\n/)
      .map((subtitle) =>
        subtitle
          .split('\n')
          .map((line) => line.trim())
          .filter(Boolean)
          .join('\n'),
      )
      .filter(Boolean)
    blocks.push(subtitles)
  }

  for (const line of text.replace(/\r\n/g, '\n').split('\n')) {
    if (SCENE_LINE.test(line)) {
      flush()
      lines = []
      started = true
    } else {
      lines.push(line)
    }
  }
  flush()
  return blocks
}

/** 대본 글의 문제. 없으면 undefined */
export function scriptIssue(blocks: string[][]) {
  if (blocks.length < MIN_SCENES) return `장면은 ${MIN_SCENES}개 이상이어야 합니다 (지금 ${blocks.length}개)`
  if (blocks.length > MAX_SCENES) return `장면은 ${MAX_SCENES}개까지입니다 (지금 ${blocks.length}개)`
  const empty = blocks.findIndex((subtitles) => subtitles.length === 0)
  if (empty >= 0) return `${empty + 1}번 장면에 대본이 없습니다`
  for (const [index, subtitles] of blocks.entries()) {
    for (const [i, subtitle] of subtitles.entries()) {
      const issue = subtitleIssue(subtitle)
      if (issue) return `${index + 1}번 장면 ${i + 1}번째 자막: ${issue}`
    }
  }
  return undefined
}

/** 고친 대본을 장면에 입힌다. i번째 장면은 기존 i번째 장면의 이미지·움직임을 쓰고, 새 장면은 앞 장면 이미지를 이어 쓴다 */
export function applyScript(scenes: Scene[], blocks: string[][]): Scene[] {
  const next: Scene[] = []
  blocks.forEach((subtitles, index) => {
    const base = scenes[index]
    const previous = next[index - 1]
    next.push({
      id: base?.id ?? newSceneId(),
      role: base?.role ?? 'body',
      caption: base?.caption ?? '',
      asset_id: base ? base.asset_id : (previous?.asset_id ?? null),
      motion: base?.motion ?? previous?.motion ?? 'zoom_in',
      subtitles,
      narration: narrationFromSubtitles(subtitles),
    })
  })
  return assignRoles(next)
}
