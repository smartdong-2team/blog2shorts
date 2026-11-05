import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { checkVideoReady, videoDownloadUrl } from '../../api/videos'

// 스크립트 생성을 위한 백엔드 API 연결
import { generateScript } from '../../api/scripts'

// 비디오 생성을 하는 백엔드 api 연결
import { createVideo } from '../../api/videos'

import { extractContent, } from './mockApi'
import { toPipelineScenes } from './scriptAdapter'

import { initialPipeline, pipelineReducer, renderKey } from './pipelineReducer'
import { assignRoles, estimateSec, formatSec } from './scenes'
import type { AudioSettings, ContentInput, Scene, StepId } from './types'

const imageCount = (text: string) => (text.match(/\[이미지 \d+\]/g) ?? []).length
const bodyChars = (text: string) => text.replace(/\[이미지 \d+\]/g, '').replace(/\s/g, '').length

/** 실패한 단계를 이미 표시했다는 표시 (바깥 catch에서 다시 처리하지 않도록) */
class StepFailed extends Error { }

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
  const runRender = async (
    scenes: Scene[],
    audio: AudioSettings,
    signal: AbortSignal,
  ) => {
    const missingImage = scenes.findIndex((scene) => !scene.asset_id)

    if (missingImage !== -1) {
      throw new Error(
        `${missingImage + 1}번 장면에 이미지가 지정되지 않았어.`,
      )
    }

    const request = {
      scenes: scenes.map((scene, index) => ({
        order: index + 1,
        role: scene.role,
        narration: scene.narration,
        caption: scene.caption,
        asset_id: scene.asset_id!,
      })),
      voice: null,
    }

    // 실제 백엔드는 음성 생성과 영상 렌더링을 하나의 작업으로 처리
    const result = await step(
      5,
      '영상 생성 요청 중',
      () => createVideo(request, signal),
      (response) => `영상 생성 요청 접수 · ${response.job_id}`,
    )

    console.log('영상 생성 작업:', result)
    // 생성된 영상의 작업 ID 저장
    dispatch({
      type: 'videoQueued',
      jobId: result.job_id,
    })

    // 202는 작업 접수이므로 아직 rendered 액션을 호출하지 않음
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
      console.log('백엔드에 전달할 콘텐츠:', content)


      // 2~3단계: 대본 생성 + 장면 구성
      const generated = await step(
        2,
        '대본과 장면 생성 중',
        () =>
          generateScript(
            {
              title: content.title,
              text: content.text,
              images: content.images.map((image) => ({
                asset_id: image.asset_id,
                alt: image.alt,
              })),
              target_duration_sec: 45,
            },
            signal,
          ),
        (result) => `핵심 포인트 ${result.summary.key_points.length}개`,
      )

      dispatch({ type: 'summary', summary: generated.summary })

      const scenes = await step(
        3,
        '장면 구성 중',
        async () => toPipelineScenes(generated),
        (list) =>
          `장면 ${list.length}개 · 약 ${formatSec(estimateSec(list))}`,
      )

      dispatch({ type: 'scenes', scenes })
      console.log('이미지 개수:', content.images.length)
      console.log('첫 번째 이미지:', content.images[0])
      console.log(
        '본문 이미지 위치:',
        content.text.match(/\[이미지 \d+\]/g),
      )


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

  const checkResult = async () => {
    const { jobId, scenes, audio } = stateRef.current

    if (!jobId) return

    try {
      const ready = await checkVideoReady(jobId)

      if (!ready) {
        alert('아직 영상을 제작하고 있어. 잠시 후 다시 확인해 줘.')
        return
      }

      dispatch({
        type: 'rendered',
        result: {
          duration_sec: 0,
          width: 1080,
          height: 1920,
          download_url: videoDownloadUrl(jobId),
        },
        renderedWith: renderKey(scenes, audio),
      })
    } catch (error) {
      alert(error instanceof Error ? error.message : '영상 확인에 실패했어.')
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

  return { state, dispatch, running, now, start, render, cancel, stepElapsed, stale,checkResult }
}
