import type { SceneRole } from '../../components/common/RoleBadge'
import type { StepStatus } from '../../components/common/StepCard'

// 필드 이름은 docs/api-design.md의 응답 형식에 맞춘다 (mockApi를 실제 API로 바꿀 때 그대로 쓰기 위해)

/** review: 1~3단계 후 멈추고 장면 확인 / auto: 1~5단계를 한 번에 */
export type Mode = 'review' | 'auto'

export type StepId = 1 | 2 | 3 | 4 | 5

export interface StepState {
  status: StepStatus
  message: string
  /** 실패 원인. 카드에는 "실패"만 쓰고 원인은 상태 줄에 보여준다 */
  error?: string
  startedAt?: number
  endedAt?: number
}

export type ContentInput = { kind: 'url'; url: string } | { kind: 'text'; title: string; text: string }

export interface ContentImage {
  asset_id: string
  url: string
  alt: string | null
}

export interface Content {
  title: string
  /** 문단은 줄바꿈으로 구분, 이미지 자리는 "[이미지 N]" 한 줄 (N은 1부터) */
  text: string
  images: ContentImage[]
  source_url: string | null
}

export interface ScriptSummary {
  topic: string
  key_points: string[]
}

export type Motion = 'zoom_in' | 'zoom_out' | 'pan_left' | 'pan_right'

export interface Scene {
  /** 화면 key용 (서버로 보내지 않음) */
  id: string
  role: SceneRole
  narration: string
  caption: string
  asset_id: string | null
  motion: Motion
}

export interface AudioSettings {
  voice: string
  music: string
  /** 배경음악 크기 0~100 */
  music_volume: number
}

export interface RenderResult {
  duration_sec: number
  width: number
  height: number
  /** 실제 영상 주소. 백엔드 연결 전에는 null (검은 화면) */
  download_url: string | null
}

/**
 * idle: 시작 전 / analyzing: 1~3단계 진행 / review: 장면 확인 대기 /
 * rendering: 4~5단계 진행 / done: 영상 완성 / stopped: 장면 없이 중지·실패
 */
export type Phase = 'idle' | 'analyzing' | 'review' | 'rendering' | 'done' | 'stopped'
