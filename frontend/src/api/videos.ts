import { request } from './client'
import type {
  VideoCreateRequest,
  VideoCreateResponse,
  VideoStatusResponse,
} from '../types/api'


// 영상 제작 요청
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

// 영상 파일 URL 생성
export function videoDownloadUrl(jobId: string): string {
  return `http://localhost:8000/api/v1/videos/${encodeURIComponent(jobId)}/download`
}

//제작 상태 조회
export function getVideoStatus(jobId: string): Promise<VideoStatusResponse> {
  return request<VideoStatusResponse>(
    `/api/v1/videos/${encodeURIComponent(jobId)}`,
  )
}

//완성된 MP4 파일 가져오기
export async function downloadVideo(
  downloadUrl: string,
): Promise<Blob> {
  const response = await fetch(downloadUrl)

  if (!response.ok) {
    throw new Error(`영상 다운로드 실패 (${response.status})`)
  }

  return response.blob()
}