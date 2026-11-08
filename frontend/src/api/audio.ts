import type { MusicListResponse } from '../types/api'
import { request } from './client'

/** 실제 음원 파일이 있는 배경음악 목록 */
export function listMusic(signal?: AbortSignal): Promise<MusicListResponse> {
  return request<MusicListResponse>('/api/v1/audio/music', { signal })
}
