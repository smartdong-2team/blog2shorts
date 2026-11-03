import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { audioSummary } from '../audio/options'
import { buildScenes, extractContent, generateScript, renderVideo, synthesizeAudio } from './mockApi'
import { initialPipeline, pipelineReducer, renderKey } from './pipelineReducer'
import { assignRoles, estimateSec, formatSec } from './scenes'
import type { AudioSettings, ContentInput, Scene, StepId } from './types'

const imageCount = (text: string) => (text.match(/\[이미지 \d+\]/g) ?? []).length
const bodyChars = (text: string) => text.replace(/\[이미지 \d+\]/g, '').replace(/\s/g, '').length

/** 실패한 단계를 이미 표시했다는 표시 (바깥 catch에서 다시 처리하지 않도록) */
class StepFailed extends Error {}

/** 진행 중일 때만 0.5초마다 갱신되는 현재 시각 (경과 시간 표시용) */
function useNow(active: boolean) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!active) return
    const timer = setInterval(() => setNow(Date.now()), 500)
    return () => clearInterval(timer)
  }, [active])
  return now
}

export function usePipeline() {
  const [state, dispatch] = useReducer(pipelineReducer, initialPipeline)
  const abortRef = useRef<AbortController | null>(null)
  const stateRef = useRef(state)
  useEffect(() => {
    stateRef.current = state
  })
  useEffect(() => () => abortRef.current?.abort(), [])

  const running = state.phase === 'analyzing' || state.phase === 'rendering'
  const now = useNow(running)

  // 한 단계 실행: 시작·완료·실패를 단계 카드에 기록
  const step = useCallback(
    async <T,>(id: StepId, message: string, run: () => Promise<T>, doneMessage: (result: T) => string) => {
      dispatch({ type: 'stepStart', step: id, message, now: Date.now() })
      try {
        const result = await run()
        dispatch({ type: 'stepDone', step: id, message: doneMessage(result), now: Date.now() })
        return result
      } catch (error) {
        if (abortRef.current?.signal.aborted) throw error
        const reason = error instanceof Error ? error.message : '알 수 없는 오류'
        dispatch({ type: 'stepFail', step: id, message: `실패: ${reason}`, now: Date.now() })
        throw new StepFailed(reason)
      }
    },
    [],
  )

  const begin = () => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    return controller.signal
  }

  const handleError = (signal: AbortSignal, error: unknown) => {
    if (signal.aborted) {
      // 새 실행이 시작돼서 중단된 경우는 표시하지 않는다
      if (abortRef.current?.signal === signal) dispatch({ type: 'stopped', message: '중지됨', now: Date.now() })
      return
    }
    if (!(error instanceof StepFailed)) console.error(error)
  }

  // 4~5단계
  const runRender = async (scenes: Scene[], audio: AudioSettings, signal: AbortSignal) => {
    await step(4, '목소리·음악 입히는 중', () => synthesizeAudio(scenes, audio, signal), () => audioSummary(audio))
    const result = await step(
      5,
      '장면 이어 붙이는 중',
      () => renderVideo(scenes, signal),
      (r) => `약 ${formatSec(r.duration_sec)} · ${r.width}×${r.height}`,
    )
    dispatch({ type: 'rendered', result, renderedWith: renderKey(scenes, audio) })
  }

  /** 1단계부터 시작. 검토 모드는 3단계 후 멈추고, 자동 모드는 5단계까지 */
  const start = async (input: ContentInput) => {
    const signal = begin()
    const mode = stateRef.current.mode
    dispatch({ type: 'runStart', phase: 'analyzing' })
    try {
      const content = await step(
        1,
        input.kind === 'url' ? '블로그에서 본문·이미지 가져오는 중' : '붙여 넣은 본문 정리 중',
        () => extractContent(input, signal),
        (c) => `본문 ${bodyChars(c.text).toLocaleString()}자 · 이미지 ${imageCount(c.text) || c.images.length}장`,
      )
      dispatch({ type: 'content', content })

      const summary = await step(
        2,
        '핵심 내용 뽑는 중',
        () => generateScript(content, signal),
        (s) => `핵심 포인트 ${s.key_points.length}개`,
      )
      dispatch({ type: 'summary', summary })

      const scenes = await step(
        3,
        'HOOK·본문·CTA 나누는 중',
        () => buildScenes(content, summary, signal),
        (list) => `장면 ${list.length}개 · 약 ${formatSec(estimateSec(list))}`,
      )
      dispatch({ type: 'scenes', scenes })

      if (mode === 'review') {
        dispatch({ type: 'waitReview' })
        return
      }
      dispatch({ type: 'runStart', phase: 'rendering' })
      await runRender(assignRoles(scenes), stateRef.current.audio, signal)
    } catch (error) {
      handleError(signal, error)
    }
  }

  /** 지금 장면·음성 설정으로 4~5단계 실행 (검토 후 "영상 만들기", 완성 후 "다시 만들기") */
  const render = async () => {
    const { scenes, audio } = stateRef.current
    const signal = begin()
    dispatch({ type: 'runStart', phase: 'rendering' })
    try {
      await runRender(scenes, audio, signal)
    } catch (error) {
      handleError(signal, error)
    }
  }

  const cancel = () => abortRef.current?.abort()

  /** 단계 카드 아래 경과 시간 */
  const stepElapsed = (id: StepId) => {
    const { startedAt, endedAt } = state.steps[id]
    if (startedAt == null) return null
    return Math.max(0, ((endedAt ?? now) - startedAt) / 1000)
  }

  const stale = state.result != null && state.renderedWith !== renderKey(state.scenes, state.audio)

  return { state, dispatch, running, now, start, render, cancel, stepElapsed, stale }
}
