import { request } from './client'
import type {
  VideoCreateRequest,
  VideoCreateResponse,
  VideoStatusResponse,
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

export function getVideoStatus(jobId: string): Promise<VideoStatusResponse> {
  return request<VideoStatusResponse>(
    `/api/v1/videos/${encodeURIComponent(jobId)}`,
  )
}