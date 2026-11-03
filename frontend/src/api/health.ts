import type { HealthResponse } from '../types/api'
import { request } from './client'

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return request<HealthResponse>('/api/v1/health', { signal })
}
