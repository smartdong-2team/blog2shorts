import { SAMPLE_SCENES, SAMPLE_SUMMARY } from './mockData'
import { assignRoles, estimateSec, newSceneId } from './scenes'
import { extractBlogContent } from '../../api/content'
import type { AudioSettings, Content, ContentInput, RenderResult, Scene, ScriptSummary } from './types'

// 백엔드 연결 전 목업. 함수 이름·인자는 docs/api-design.md 엔드포인트에 대응한다.
// 실제 API로 바꿀 때는 이 파일의 함수 본문만 fetch 호출로 교체한다.

function wait(ms: number, signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    if (signal.aborted) return reject(signal.reason)
    const timer = setTimeout(resolve, ms)
    signal.addEventListener(
      'abort',
      () => {
        clearTimeout(timer)
        reject(signal.reason)
      },
      { once: true },
    )
  })
}

function sentences(text: string) {
  return text
    .replace(/\[이미지 \d+\]/g, '')
    .split(/(?<=[.!?。])\s+|\n+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
}

const cut = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1)}…` : s)

/** POST /content/extract (URL) — 직접 입력이면 서버를 거치지 않고 그대로 쓴다 */
// export async function extractContent(input: ContentInput, signal: AbortSignal): Promise<Content> {
//   await wait(input.kind === 'url' ? 2200 : 600, signal)
//   if (input.kind === 'url') return { ...SAMPLE_CONTENT, source_url: input.url }
//   return { title: input.title.trim() || '직접 입력한 글', text: input.text.trim(), images: [], source_url: null }
// }

export async function extractContent(
  input: ContentInput,
  signal: AbortSignal,
): Promise<Content> {
  // 직접 입력은 서버 추출 없이 사용
  if (input.kind === 'text') {
    return {
      title: input.title.trim() || '직접 입력한 글',
      text: input.text.trim(),
      images: [],
      source_url: null,
    }
  }

  // URL 입력은 실제 백엔드 API 호출
  const response = await extractBlogContent(
    { url: input.url },
    signal,
  )

  return {
    title: response.title,
    text: response.text,
    images: response.images.map((image) => ({
      asset_id: image.asset_id,
      url: new URL(
        image.url,
        import.meta.env.VITE_API_BASE_URL,
      ).href,
      alt: image.alt,
    })),
    source_url: response.source.url,
  }
}


/** POST /scripts/generate 의 summary 부분 */
export async function generateScript(content: Content, signal: AbortSignal): Promise<ScriptSummary> {
  await wait(2600, signal)
  if (content.source_url) return SAMPLE_SUMMARY
  const list = sentences(content.text)
  return { topic: cut(content.title, 30), key_points: list.slice(0, 3).map((s) => cut(s, 50)) }
}

/** POST /scripts/generate 의 scenes 부분 */
export async function buildScenes(content: Content, _summary: ScriptSummary, signal: AbortSignal): Promise<Scene[]> {
  await wait(1800, signal)
  if (content.source_url) return SAMPLE_SCENES.map((s) => ({ ...s, id: newSceneId() }))

  const list = sentences(content.text)
  const body = list.slice(1, 4)
  const scenes: Scene[] = [list[0], ...body, '더 자세한 내용은 원문에서 확인하세요.'].map((line) => ({
    id: newSceneId(),
    role: 'body',
    narration: cut(line, 120),
    caption: cut(line, 14),
    asset_id: null,
    motion: 'zoom_in',
  }))
  // 장면은 최소 4개
  while (scenes.length < 4) {
    scenes.splice(scenes.length - 1, 0, { ...scenes[0], id: newSceneId() })
  }
  return assignRoles(scenes)
}

/** 4단계: 장면별 TTS + 배경음악 믹싱 */
export async function synthesizeAudio(scenes: Scene[], _audio: AudioSettings, signal: AbortSignal) {
  await wait(1200 + scenes.length * 400, signal)
}

/** POST /videos → GET /videos/{job_id} 폴링 결과 */
export async function renderVideo(scenes: Scene[], signal: AbortSignal): Promise<RenderResult> {
  await wait(3000, signal)
  return { duration_sec: estimateSec(scenes), width: 1080, height: 1920, download_url: null }
}
