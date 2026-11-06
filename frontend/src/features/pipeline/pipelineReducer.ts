import { DEFAULT_AUDIO } from '../audio/options'
import { MAX_SCENES, MIN_SCENES, assignRoles, newSceneId } from './scenes'
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
  4: '음성과 음악',
  5: '영상 제작',
}

export const STEP_IDS: StepId[] = [1, 2, 3, 4, 5]

export interface PipelineState {
  mode: Mode
  phase: Phase
  steps: Record<StepId, StepState>
  content: Content | null
  summary: ScriptSummary | null
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
  | { type: 'scenes'; scenes: Scene[] }
  | { type: 'rendered'; result: RenderResult; renderedWith: string }
  | { type: 'editScene'; index: number; patch: Partial<Omit<Scene, 'id' | 'role'>> }
  | { type: 'moveScene'; index: number; delta: -1 | 1 }
  | { type: 'addScene' }
  | { type: 'removeScene'; index: number }
  | { type: 'addImage'; image: ContentImage; sceneIndex: number }
  | { type: 'audio'; patch: Partial<AudioSettings> }
  | { type: 'videoQueued'; jobId: string }
  | { type: 'videoFailed'; error: string; now: number }

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
      return { ...state, phase: 'rendering', steps, result: null,jobId: null, }
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
      return { ...next, phase: next.scenes.length ? 'review' : 'stopped' }
    }

    case 'waitReview': {
      const next = setStep(state, 4, { status: 'waiting', message: '장면 확인 후 진행' })
      return { ...next, phase: 'review' }
    }

    case 'content':
      return { ...state, content: action.content }

    case 'summary':
      return { ...state, summary: action.summary }

    case 'scenes':
      return { ...state, scenes: assignRoles(action.scenes) }

    case 'rendered':
      return { ...state, phase: 'done', result: action.result, renderedWith: action.renderedWith }

    case 'editScene':
      return {
        ...state,
        scenes: state.scenes.map((s, i) => (i === action.index ? { ...s, ...action.patch } : s)),
      }
    case 'videoQueued':
      return {
        ...state,
        jobId: action.jobId,
        phase: 'review',
      }

    case 'videoFailed': {
      const next = setStep(state, 5, { status: 'error', message: '실패', error: action.error, endedAt: action.now })
      return { ...next, jobId: null }
    }

    case 'moveScene': {
      const to = action.index + action.delta
      if (to < 0 || to >= state.scenes.length) return state
      const scenes = [...state.scenes]
        ;[scenes[action.index], scenes[to]] = [scenes[to], scenes[action.index]]
      return { ...state, scenes: assignRoles(scenes) }
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
        caption: '',
        asset_id: state.scenes[last]?.asset_id ?? null,
        motion: 'zoom_in',
      })
      return { ...state, scenes: assignRoles(scenes) }
    }

    case 'removeScene':
      if (state.scenes.length <= MIN_SCENES) return state
      return { ...state, scenes: assignRoles(state.scenes.filter((_, i) => i !== action.index)) }

    case 'addImage': {
      if (!state.content) return state
      const content = { ...state.content, images: [...state.content.images, action.image] }
      const scenes = state.scenes.map((s, i) => (i === action.sceneIndex ? { ...s, asset_id: action.image.asset_id } : s))
      return { ...state, content, scenes }
    }

    case 'audio':
      return { ...state, audio: { ...state.audio, ...action.patch } }
  }
}
