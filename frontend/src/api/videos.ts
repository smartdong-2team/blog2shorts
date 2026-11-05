import { request } from './client'
import type {
  VideoCreateRequest,
  VideoCreateResponse,
} from '../types/api'


export function createVideo(
  data: VideoCreateRequest,
  signal?: AbortSignal,
): Promise<VideoCreateResponse> {
  return request<VideoCreateResponse>(
    '/api/v1/videos',
    {
      method: 'POST',
      body: JSON.stringify(data),
      signal,
    },
  )
}

export function videoDownloadUrl(jobId: string): string {
  return `http://localhost:8000/api/v1/videos/${encodeURIComponent(jobId)}/download`
}

export async function checkVideoReady(jobId: string): Promise<boolean> {
  const response = await fetch(videoDownloadUrl(jobId), {
    method: 'HEAD',
  })

  if (response.status === 409) return false

  if (!response.ok) {
    throw new Error(`영상 확인 실패 (${response.status})`)
  }

  return true
}