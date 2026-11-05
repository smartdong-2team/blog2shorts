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