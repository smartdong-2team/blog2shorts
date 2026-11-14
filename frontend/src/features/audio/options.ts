import type { AudioSettings } from '../pipeline/types'

// edge_*는 무료 Edge 음성, 나머지는 OpenAI 음성(크레딧 필요)
export const VOICE_OPTIONS = [
  { value: 'edge_injoon', label: '인준 (남성)' },
  { value: 'edge_sunhi', label: '선희 (여성)' },
  { value: 'edge_hyunsu', label: '현수 (남성)' },
  { value: 'calm_female', label: '차분한 여성 (OpenAI)' },
  { value: 'bright_female', label: '밝은 여성 (OpenAI)' },
  { value: 'clear_male', label: '또렷한 남성 (OpenAI)' },
  { value: 'low_male', label: '낮은 남성 (OpenAI)' },
]

export const MUSIC_OPTIONS = [
  { value: 'none', label: '배경음악 없음' },
  { value: 'salsa_new_york', label: '살사 (Salsa Estilo New York 03)' },
  { value: 'soft_piano', label: '잔잔한 피아노' },
  { value: 'light_acoustic', label: '경쾌한 어쿠스틱' },
  { value: 'dreamy_synth', label: '몽환적인 신스' },
]

export const NO_MUSIC = 'none'

export const DEFAULT_AUDIO: AudioSettings = { voice: 'edge_injoon', music: NO_MUSIC, music_volume: 30 }

const labelOf = (options: { value: string; label: string }[], value: string) =>
  options.find((o) => o.value === value)?.label ?? value

export const voiceLabel = (value: string) => labelOf(VOICE_OPTIONS, value)
export const musicLabel = (value: string) => labelOf(MUSIC_OPTIONS, value)

/** "차분한 여성 · 잔잔한 피아노 30%" */
export function audioSummary(audio: AudioSettings) {
  const music = audio.music === 'none' ? '배경음악 없음' : `${musicLabel(audio.music)} ${audio.music_volume}%`
  return `${voiceLabel(audio.voice)} · ${music}`
}
