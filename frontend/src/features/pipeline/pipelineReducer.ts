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

export const STEP_TITLES: Record<StepId, string> = {
  1: '컨텐츠 가져오기',
  2: '대본 구상하기',
  3: '장면',
  4: '편집',
  5: '영상 제작',
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
  /** 마지막 렌더에 쓴 장면·음성 설정. 지금 값과 다르면 "다시 만들기" 안내 */
  renderedWith: string | null
  jobId: string | null
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
  | { type: 'videoFailed'; error: string; now: number }
  | { type: 'editSubtitles'; index: number; subtitles: string[] }

const idleSteps = (): Record<StepId, StepState> => ({
  1: { status: 'idle', message: '본문·이미지 대기' },
  2: { status: 'idle', message: '대기' },
  3: { status: 'idle', message: '대기' },
  4: { status: 'idle', message: '대기' },
  5: { status: 'idle', message: '대기' },
})

export const initialPipeline: PipelineState = {
  mode: 'review',
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
      // 4~5단계만 다시: 이전 결과를 지우고 두 단계를 대기로
      const steps = { ...state.steps, 4: idleSteps()[4], 5: idleSteps()[5] }
      return { ...state, phase: 'rendering', steps, result: null, jobId: null, }
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
      return { ...next, phase: next.scenes.length ? 'review' : 'stopped', jobId: null }
    }

    case 'waitReview': {
      const next = setStep(state, 4, { status: 'waiting', message: '장면 확인 후 진행' })
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

    case 'rendered':
      return {
        ...setStep(state, 5, { status: 'done', message: '영상 완성', endedAt: action.now }),
        phase: 'done',
        result: action.result,
        renderedWith: action.renderedWith,
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
        // 완성될 때까지 5단계를 진행 중으로 두어 중지 버튼을 보여준다
        ...setStep(state, 5, { status: 'running', message: '음성·자막·영상 합성 중', endedAt: undefined }),
        jobId: action.jobId,
        phase: 'rendering',
      }

    // 영상 제작 실패
    case 'videoFailed': {
      const next = setStep(state, 5, {
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

    case 'audio':
      return { ...state, audio: { ...state.audio, ...action.patch } }
  }


}
