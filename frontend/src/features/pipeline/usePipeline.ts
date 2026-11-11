import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { ApiError } from '../../api/client'
import { cancelVideo, getVideoStatus, videoDownloadUrl } from '../../api/videos'

// 스크립트 생성을 위한 백엔드 API 연결
import { generateScript } from '../../api/scripts'

// 비디오 생성을 하는 백엔드 api 연결
import { createVideo } from '../../api/videos'

import { extractContent, } from './mockApi'
import { toPipelineScenes } from './scriptAdapter'

import { initialPipeline, pipelineReducer, renderKey } from './pipelineReducer'
import { assignRoles, estimateSec, formatSec, subtitlePagesOf } from './scenes'
import type { ContentInput, Scene, StepId } from './types'

const imageCount = (text: string) => (text.match(/\[이미지 \d+\]/g) ?? []).length
const bodyChars = (text: string) => text.replace(/\[이미지 \d+\]/g, '').replace(/\s/g, '').length

/** 실패한 단계를 이미 표시했다는 표시 (바깥 catch에서 다시 처리하지 않도록) */
class StepFailed extends Error { }

const VIDEO_POLL_MS = 2000

const errorMessage = (error: unknown) => (error instanceof Error ? error.message : '알 수 없는 오류')

interface UsePipelineOptions {
  /** 사용자에게 알려야 할 실패가 생겼을 때 */
  onError: (message: string) => void
  /** 새 실행을 시작할 때 (지난 오류 알림 정리용) */
  onRunStart: () => void
}

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

export function usePipeline({ onError, onRunStart }: UsePipelineOptions) {
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
        const reason = errorMessage(error)
        dispatch({ type: 'stepFail', step: id, error: reason, now: Date.now() })
        onError(reason)
        throw new StepFailed(reason)
      }
    },
    [onError],
  )

  const failVideo = useCallback(
    (reason: string) => {
      dispatch({ type: 'videoFailed', error: reason, now: Date.now() })
      onError(reason)
    },
    [onError],
  )

  /** 상태 조회 실패 처리: 사라진 작업은 5단계 실패, 그 외는 알림만 */
  const handleStatusError = useCallback(
    (error: unknown) => {
      if (error instanceof ApiError && error.status === 404) failVideo(error.message)
      else onError(errorMessage(error))
    },
    [failVideo, onError],
  )

  // 영상 작업은 백그라운드에서 돌므로 실패를 놓치지 않도록 상태를 계속 확인한다
  const { jobId } = state
  const hasResult = state.result != null
  useEffect(() => {
    if (!jobId || hasResult) return
    let stopped = false
    let timer: ReturnType<typeof setTimeout>

    const poll = async () => {
      try {
        const { status, error, progress } = await getVideoStatus(jobId)
        if (stopped) return
        if (progress) dispatch({ type: 'videoProgress', progress, now: Date.now() })
        if (status === 'failed') {
          failVideo(error?.message ?? '영상 생성에 실패했습니다.')
          return
        }

        if (status === 'cancelled') {
          dispatch({ type: 'stopped', message: '중지됨', now: Date.now() })
          return
        }

        /** 기존에는 상태가 completed가 되면 그냥 종료했지만, 이제는 렌더링 결과를 확인하고 rendered 액션을 호출하도록 변경 */
        if (status === 'completed') {
          const { scenes, audio } = stateRef.current

          dispatch({
            type: 'rendered',
            result: {
              duration_sec: estimateSec(scenes),
              width: 1080,
              height: 1920,
              download_url: videoDownloadUrl(jobId),
            },
            renderedWith: renderKey(scenes, audio),
            now: Date.now(),
          })

          return
        }
        timer = setTimeout(poll, VIDEO_POLL_MS)
      } catch (error) {
        if (!stopped) handleStatusError(error)
      }
    }

    timer = setTimeout(poll, VIDEO_POLL_MS)
    return () => {
      stopped = true
      clearTimeout(timer)
    }
  }, [jobId, hasResult, failVideo, handleStatusError])

  const begin = () => {
    onRunStart()
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
    signal: AbortSignal,
    hookText: string,
  ) => {
    const { audio } = stateRef.current

    const request = {
      scenes: scenes.map((scene, index) => ({
        order: index + 1,
        role: scene.role,
        narration: scene.narration,
        // 화면 제목은 영상에 쓰이지 않지만 서버가 빈 값을 받지 않는다. 직접 추가한 장면은 비어 있다
        caption: scene.caption.trim() || scene.narration.slice(0, 30),
        asset_id: scene.asset_id!,
        motion: scene.motion,
        subtitle_pages: subtitlePagesOf(scene),
      })),
      voice: audio.voice,
      music: audio.music,
      music_volume: audio.music_volume,
      hook_text: hookText,
    }

    // 서버는 한 작업 안에서 음성(4단계) → 영상 합성(5단계)을 이어서 한다. 진행 상황은 상태 조회로 받는다
    const result = await step(
      4,
      '영상 생성 요청 중',
      async () => {
        const missingImage = scenes.findIndex((scene) => !scene.asset_id)
        if (missingImage !== -1) {
          throw new Error(`${missingImage + 1}번 장면에 이미지가 지정되지 않았습니다.`)
        }

        return createVideo(request, signal)
      },
      (response) => `영상 생성 요청 접수 · ${response.job_id}`,
    )

    // 202는 작업 접수이므로 진행 정보를 받을 때까지 4단계를 진행 중으로 둔다
    dispatch({
      type: 'videoQueued',
      jobId: result.job_id,
      now: Date.now(),
    })
  }
  /** 1단계부터 시작. 검토 모드는 장면이 나오면(3단계 편집) 멈추고, 자동 모드는 5단계까지 */
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

      // 2단계: 대본 생성 + 자막 카드로 변환
      const { generated, scenes } = await step(
        2,
        '대본과 장면 생성 중',
        async () => {
          const generated = await generateScript(
            {
              title: content.title,
              // 이미지 자리 표시는 원문 화면용이라 대본 요청에서는 뺀다 (이미지는 images로 따로 보냄)
              text: content.text.replace(/^\[이미지 \d+\]\n?/gm, '').trim(),
              images: content.images.map((image) => ({
                asset_id: image.asset_id,
                alt: image.alt,
              })),
              target_duration_sec: 45,
            },
            signal,
          )
          return { generated, scenes: toPipelineScenes(generated) }
        },
        ({ scenes }) => `장면 ${scenes.length}개 · 약 ${formatSec(estimateSec(scenes))}`,
      )

      dispatch({ type: 'summary', summary: generated.summary })
      dispatch({ type: 'hookText', hookText: generated.hook_text })

      dispatch({ type: 'scenes', scenes })

      if (mode === 'review') {
        dispatch({ type: 'waitReview' })
        return
      }
      dispatch({ type: 'runStart', phase: 'rendering' })
      await runRender(assignRoles(scenes), signal, generated.hook_text)
    } catch (error) {
      handleError(signal, error)
    }
  }

  /** 지금 장면·음성 설정으로 4~5단계 실행 (검토 후 "영상 제작", 완성 후 "영상 다시 제작") */
  const render = async () => {
    const { scenes } = stateRef.current

    // 영상 생성 전에 이미지가 없는 장면 확인
    const missingImage = scenes.findIndex(
      (scene) => !scene.asset_id
    )

    if (missingImage !== -1) {
      alert(
        `${missingImage + 1}번 장면에 이미지가 없습니다.\n이미지를 선택한 후 다시 영상 제작을 시도해주세요.`
      )
      return
    }

    // 검증을 통과한 경우에만 영상 생성 시작
    const signal = begin()

    dispatch({
      type: 'runStart',
      phase: 'rendering',
    })

    try {
      await runRender(scenes, signal, stateRef.current.hookText)
    } catch (error) {
      handleError(signal, error)
    }
  }

  /** 진행 중인 요청을 끊고, 서버에 넘어간 영상 작업도 함께 중지한다 */
  const cancel = () => {
    abortRef.current?.abort()

    const { jobId: runningJob, result } = stateRef.current
    if (!runningJob || result) return

    dispatch({ type: 'stopped', message: '중지됨', now: Date.now() })
    cancelVideo(runningJob).catch((error) => onError(errorMessage(error)))
  }

  /**
   * 영상 작업 진행률(0~1)과 남은 시간(초). 서버가 장면 단위로 알려 주므로,
   * 마지막으로 받은 시점의 속도로 남은 시간을 구하고 그 뒤로는 시간이 가는 만큼 줄인다.
   */
  const videoEta = () => {
    const info = state.videoProgress
    const startedAt = state.steps[4].startedAt
    if (!info || startedAt == null || state.phase !== 'rendering') return null
    const elapsedAtUpdate = (info.at - startedAt) / 1000
    // 너무 이른 추정은 크게 흔들리므로 5% 이상 진행된 뒤부터 남은 시간을 보여 준다
    const remainingSec =
      info.progress >= 0.05 ? Math.max(1, (elapsedAtUpdate * (1 - info.progress)) / info.progress - (now - info.at) / 1000) : null
    return { progress: info.progress, remainingSec }
  }

  /** 단계 카드 아래 경과 시간 */
  const stepElapsed = (id: StepId) => {
    const { startedAt, endedAt } = state.steps[id]
    if (startedAt == null) return null
    return Math.max(0, ((endedAt ?? now) - startedAt) / 1000)
  }

  const stale = state.result != null && state.renderedWith !== renderKey(state.scenes, state.audio)

  return { state, dispatch, running, now, start, render, cancel, stepElapsed, videoEta, stale }
}
