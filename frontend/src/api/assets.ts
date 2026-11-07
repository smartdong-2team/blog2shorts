import type { ContentImage } from '../features/pipeline/types'
import { request } from './client'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

interface UploadAssetResponse {
  asset_id: string
  url: string
  width: number
  height: number
}

export async function uploadImage(
  file: File,
  signal?: AbortSignal,
): Promise<ContentImage> {
  const formData = new FormData()
  formData.append('file', file)

  const data = await request<UploadAssetResponse>(
    '/api/v1/assets/upload',
    {
      method: 'POST',
      body: formData,
      signal,
    },
  )

  return {
    asset_id: data.asset_id,
    url: `${API_BASE_URL}${data.url}`,
    alt: file.name,
  }
}