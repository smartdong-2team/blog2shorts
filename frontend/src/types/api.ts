import type { Motion } from "../features/pipeline/types"

export interface HealthResponse {
  status: 'ok'
  app_env: string
  version: string
}

// 백엔드 공통 오류 포맷: { error: { code, message, details } }
export interface ApiErrorBody {
  error: {
    code: string
    message: string
    details?: unknown
  }
}


export interface ScriptImage {
  asset_id: string
  alt: string | null
}

export interface ScriptGenerateRequest {
  title?: string | null
  text: string
  images?: ScriptImage[]
  target_duration_sec?: number
}

export interface ScriptSummary {
  topic: string
  key_points: string[]
}

export type ScriptSceneRole = 'hook' | 'body' | 'cta'

export interface ScriptScene {
  order: number
  role: ScriptSceneRole
  narration: string
  caption: string
  subtitle_pages: string[][]
  asset_id: string | null
}

export interface ScriptGenerateResponse {
  summary: ScriptSummary
  scenes: ScriptScene[]
  estimated_duration_sec: number
  hook_text: string
}


export interface ContentExtractRequest {
  url: string
}

export interface ContentExtractResponse {
  source: {
    platform: string
    blog_id: string
    log_no: string
    url: string
  }
  title: string
  text: string
  images: {
    asset_id: string
    url: string
    width: number
    height: number
    alt: string | null
  }[]
}


export interface MusicListResponse {
  tracks: { id: string; label: string }[]
}

// api - videos.ts 관련 타입 정리
export interface VideoCreateRequest {
  scenes: {
    order: number
    role: string
    narration: string
    caption: string
    asset_id: string
    motion: Motion
    subtitle_pages: string[][]
  }[]
  voice: string | null
  music: string
  music_volume: number
  hook_text?: string
}

export interface VideoCreateResponse {
  job_id: string
  status: string
  status_url: string
}

/** 영상 작업 진행 상황. tts: 장면별 음성, rendering: 장면별 영상, finishing: 연결·배경음악 */
export interface VideoProgressInfo {
  stage: 'tts' | 'rendering' | 'finishing'
  done: number
  total: number
  /** 전체 작업 기준 0~1 */
  progress: number
}

export interface VideoStatusResponse {
  job_id: string
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled'
  error: { code: string; message: string } | null
  /** 처리 중일 때만 */
  progress?: VideoProgressInfo | null
}
