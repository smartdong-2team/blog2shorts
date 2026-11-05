
import type {
  ContentExtractRequest,
  ContentExtractResponse,
} from '../types/api'
import { request } from './client'

export function extractBlogContent(
  data: ContentExtractRequest,
  signal?: AbortSignal,
): Promise<ContentExtractResponse> {
  return request<ContentExtractResponse>(
    '/api/v1/content/extract',
    {
      method: 'POST',
      body: JSON.stringify(data),
      signal,
    },
  )
}
