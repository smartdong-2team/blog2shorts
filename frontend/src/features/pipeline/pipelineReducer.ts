import { DEFAULT_AUDIO } from '../audio/options'
import { MAX_SCENES, MIN_SCENES, assignRoles, narrationFromSubtitles, newSceneId, subtitlesOf } from './scenes'
import type {
  AudioSettings,
  Content,
  ContentImage,
  Mode,
  Phase,
  RenderResult,
  Scene,
  ScriptSummary,
  StepId,
  StepState,
} from './types'
import type { VideoProgressInfo } from '../../types/api'

export const STEP_TITLES: Record<StepId, string> = {
  1: '컨텐츠 가져오기',
  2: '대본·장면 만들기',
  3: '편집',
  4: '음성 만들기',
  5: '영상 합성',
}

export const STEP_IDS: StepId[] = [1, 2, 3, 4, 5]

export interface PipelineState {
  mode: Mode
  phase: Phase
  steps: Record<StepId, StepState>
  content: Content | null
  summary: ScriptSummary | null
  hookText: string
  scenes: Scene[]
  audio: AudioSettings
  result: RenderResult | null
  /** 마지막 렌더에 쓴 장면·음성 설정. 지금 값과 다르면 "영상 다시 제작" 안내 */
  renderedWith: string | null
  jobId: string | null
  /** 영상 작업 진행 상황과 받은 시각(남은 시간 계산용) */
  videoProgress: (VideoProgressInfo & { at: number }) | null
}

export type PipelineAction =
  | { type: 'setMode'; mode: Mode }
  | { type: 'reset' }
  | { type: 'runStart'; phase: 'analyzing' | 'rendering' }
  | { type: 'stepStart'; step: StepId; message: string; now: number }
  | { type: 'stepDone'; step: StepId; message: string; now: number }
  | { type: 'stepFail'; step: StepId; error: string; now: number }
  | { type: 'stopped'; message: string; now: number }
  | { type: 'waitReview' }
  | { type: 'content'; content: Content }
  | { type: 'summary'; summary: ScriptSummary }
  | { type: 'hookText'; hookText: string }
  | { type: 'scenes'; scenes: Scene[] }
  | { type: 'rendered'; result: RenderResult; renderedWith: string; now: number }
  | { type: 'editScene'; index: number; patch: Partial<Omit<Scene, 'id' | 'role'>> }
  | { type: 'addScene' }
  | { type: 'removeScene'; index: number }
  | {
    type: 'setSceneImage'
    index: number
    /** 이 자막부터 이미지를 바꾼다. 0이면 장면 전체 */
    subtitleIndex: number
    assetId: string | null
  }
  | { type: 'addImage'; image: ContentImage; sceneIndex: number; subtitleIndex: number }
  | { type: 'audio'; patch: Partial<AudioSettings> }
  | { type: 'videoQueued'; jobId: string; now: number }
  | { type: 'videoProgress'; progress: VideoProgressInfo; now: number }
  | { type: 'videoFailed'; error: string; now: number }
  | { type: 'editSubtitles'; index: number; subtitles: string[] }
  /** 전체 보기 적용: 장면 전체를 바꾼다 */
  | { type: 'replaceScenes'; scenes: Scene[] }
  /** 장면에 넣지 않고 원문 이미지 목록에만 추가 (전체 보기에서 올린 이미지) */
  | { type: 'contentImage'; image: ContentImage }

const idleSteps = (): Record<StepId, StepState> => ({
  1: { status: 'idle', message: '대기' },
  2: { status: 'idle', message: '대기' },
  3: { status: 'idle', message: '대기' },
  4: { status: 'idle', message: '대기' },
  5: { status: 'idle', message: '대기' },
})

export const initialPipeline: PipelineState = {
  mode: 'auto',
  phase: 'idle',
  steps: idleSteps(),
  content: null,
  summary: null,
  hookText: '',
  scenes: [],
  audio: DEFAULT_AUDIO,
  result: null,
  renderedWith: null,
  jobId: null,
  videoProgress: null,
}

/** 렌더 입력(장면·음성 설정)을 비교용 문자열로 */
export const renderKey = (scenes: Scene[], audio: AudioSettings) => JSON.stringify({ scenes, audio })

const setStep = (state: PipelineState, step: StepId, patch: Partial<StepState>) => ({
  ...state,
  steps: { ...state.steps, [step]: { ...state.steps[step], ...patch } },
})

/** 두 장면을 하나로 합친다. 앞 장면의 제목과 움직임을 쓴다 */
function joinScenes(first: Scene, second: Scene): Scene {
  const subtitles = [...subtitlesOf(first), ...subtitlesOf(second)]
  return { ...first, subtitles, narration: narrationFromSubtitles(subtitles) }
}

/**
 * 장면 이미지를 바꾼다. 중간 자막부터 바꾸면 그 자막부터 새 장면이 된다.
 * 바꾼 뒤 앞뒤 장면과 이미지가 같아지면 다시 한 장면으로 합친다.
 * 음성과 사진 움직임이 장면 단위라, 같은 이미지가 여러 장면으로 나뉘면 끊겨 보이기 때문이다.
 */
function setSceneImage(scenes: Scene[], index: number, subtitleIndex: number, assetId: string | null): Scene[] {
  const original = scenes[index]
  if (!original || original.asset_id === assetId) return scenes

  const subtitles = subtitlesOf(original)
  const next = [...scenes]
  let target = index

  if (subtitleIndex > 0 && subtitleIndex < subtitles.length && scenes.length < MAX_SCENES) {
    const before = subtitles.slice(0, subtitleIndex)
    const after = subtitles.slice(subtitleIndex)
    next.splice(
      index,
      1,
      { ...original, subtitles: before, narration: narrationFromSubtitles(before) },
      { ...original, id: newSceneId(), subtitles: after, narration: narrationFromSubtitles(after), asset_id: assetId },
    )
    target = index + 1
  } else {
    next[index] = { ...original, asset_id: assetId }
  }

  const following = next[target + 1]
  if (following && following.asset_id === assetId && next.length > MIN_SCENES) {
    next.splice(target, 2, joinScenes(next[target], following))
  }

  const previous = next[target - 1]
  if (previous && previous.asset_id === assetId && next.length > MIN_SCENES) {
    next.splice(target - 1, 2, joinScenes(previous, next[target]))
  }

  return assignRoles(next)
}

export function pipelineReducer(state: PipelineState, action: PipelineAction): PipelineState {
  switch (action.type) {
    case 'setMode':
      return { ...state, mode: action.mode }

    case 'reset':
      return { ...initialPipeline, mode: state.mode, audio: state.audio }

    case 'runStart': {
      if (action.phase === 'analyzing') return { ...initialPipeline, mode: state.mode, audio: state.audio, phase: 'analyzing' }
      // 영상만 다시: 편집(3단계)은 지금 장면으로 확정해 완료로 두고, 음성·합성(4~5단계)은 대기로
      const steps = { ...state.steps, 3: { status: 'done' as const, message: '장면 확정' }, 4: idleSteps()[4], 5: idleSteps()[5] }
      return { ...state, phase: 'rendering', steps, result: null, jobId: null, videoProgress: null }
    }

    case 'stepStart':
      return setStep(state, action.step, { status: 'running', message: action.message, error: undefined, startedAt: action.now, endedAt: undefined })

    case 'stepDone':
      return setStep(state, action.step, { status: 'done', message: action.message, endedAt: action.now })

    case 'stepFail': {
      const next = setStep(state, action.step, { status: 'error', message: '실패', error: action.error, endedAt: action.now })
      return { ...next, phase: next.scenes.length ? 'review' : 'stopped' }
    }

    case 'stopped': {
      const running = STEP_IDS.find((id) => state.steps[id].status === 'running')
      const next = running
        ? setStep(state, running, { status: 'cancelled', message: action.message, endedAt: action.now })
        : state
      return { ...next, phase: next.scenes.length ? 'review' : 'stopped', jobId: null, videoProgress: null }
    }

    case 'waitReview': {
      const next = setStep(state, 3, { status: 'waiting', message: '장면 확인 후 진행' })
      return { ...next, phase: 'review' }
    }

    case 'content':
      return { ...state, content: action.content }

    case 'summary':
      return { ...state, summary: action.summary }

    case 'hookText':
      return { ...state, hookText: action.hookText }

    case 'scenes':
      return { ...state, scenes: assignRoles(action.scenes) }

    case 'rendered': {
      // 음성 단계가 진행 중으로 남아 있으면(진행 정보를 못 받은 채 끝난 경우) 함께 완료로
      const voiced = state.steps[4].status === 'running'
        ? setStep(state, 4, { status: 'done', message: '음성 완료', endedAt: action.now })
        : state
      const started = voiced.steps[5].startedAt == null ? { startedAt: action.now } : {}
      return {
        ...setStep(voiced, 5, { ...started, status: 'done', message: '영상 완성', endedAt: action.now }),
        phase: 'done',
        result: action.result,
        renderedWith: action.renderedWith,
        videoProgress: null,
      }
    }

    case 'editScene':
      return {
        ...state,
        scenes: state.scenes.map((s, i) => (i === action.index ? { ...s, ...action.patch } : s)),
      }

    case 'editSubtitles':
      return {
        ...state,
        scenes: state.scenes.map((s, i) =>
          i === action.index
            ? { ...s, subtitles: action.subtitles, narration: narrationFromSubtitles(action.subtitles) }
            : s,
        ),
      }

    // 영상 제작 시작 시점에 jobId를 기록, 렌더링 중에는 jobId가 존재
    case 'videoQueued':
      return {
        // 서버가 음성부터 만든다. 완성될 때까지 진행 중으로 두어 중지 버튼을 보여준다
        ...setStep(state, 4, { status: 'running', message: '장면별 음성 만드는 중', endedAt: undefined }),
        jobId: action.jobId,
        phase: 'rendering',
      }

    case 'videoProgress': {
      const { stage, done, total } = action.progress
      let next: PipelineState = { ...state, videoProgress: { ...action.progress, at: action.now } }
      if (stage === 'tts') {
        next = setStep(next, 4, { message: `장면 음성 ${done}/${total}` })
      } else {
        // 렌더링에 들어서면 음성 단계는 끝난 것
        if (next.steps[4].status === 'running') {
          next = setStep(next, 4, { status: 'done', message: `음성 ${total}개`, endedAt: action.now })
        }
        if (next.steps[5].status !== 'running') {
          next = setStep(next, 5, { status: 'running', startedAt: action.now, endedAt: undefined, message: '' })
        }
        next = setStep(next, 5, { message: stage === 'finishing' ? '장면 연결·배경음악 합치는 중' : `장면 영상 ${done}/${total}` })
      }
      return next
    }

    // 영상 제작 실패
    case 'videoFailed': {
      // 진행 중이던 단계(음성 또는 합성)를 실패로
      const failedStep: StepId = state.steps[4].status === 'running' ? 4 : 5
      const next = setStep(state, failedStep, {
        status: 'error',
        message: '실패',
        error: action.error,
        endedAt: action.now,
      })

      return {
        ...next,
        phase: 'review',
        jobId: null,
      }
    }

    case 'addScene': {
      if (state.scenes.length >= MAX_SCENES) return state
      const last = state.scenes.length - 1
      const scenes = [...state.scenes]
      // CTA 앞에 본문 장면 추가
      scenes.splice(last, 0, {
        id: newSceneId(),
        role: 'body',
        narration: '',
        subtitles: [''],
        caption: '',
        asset_id: state.scenes[last]?.asset_id ?? null,
        motion: 'zoom_in',
      })
      return { ...state, scenes: assignRoles(scenes) }
    }

    case 'setSceneImage':
      return { ...state, scenes: setSceneImage(state.scenes, action.index, action.subtitleIndex, action.assetId) }

    case 'removeScene':
      if (state.scenes.length <= MIN_SCENES) return state
      return { ...state, scenes: assignRoles(state.scenes.filter((_, i) => i !== action.index)) }

    case 'addImage': {
      if (!state.content) return state
      const content = { ...state.content, images: [...state.content.images, action.image] }
      const scenes = setSceneImage(state.scenes, action.sceneIndex, action.subtitleIndex, action.image.asset_id)
      return { ...state, content, scenes }
    }

    case 'replaceScenes':
      return { ...state, scenes: assignRoles(action.scenes) }

    case 'contentImage':
      if (!state.content) return state
      return { ...state, content: { ...state.content, images: [...state.content.images, action.image] } }

    case 'audio':
      return { ...state, audio: { ...state.audio, ...action.patch } }
  }


}
