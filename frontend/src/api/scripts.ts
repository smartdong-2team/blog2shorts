
import type {
  ScriptGenerateRequest,
  ScriptGenerateResponse,
} from '../types/api'
import { request } from './client'


export function generateScript(
  data: ScriptGenerateRequest,
  signal?: AbortSignal,
): Promise<ScriptGenerateResponse> {
  return request<ScriptGenerateResponse>(
    '/api/v1/scripts/generate',
    {
      method: 'POST',
      body: JSON.stringify(data),
      signal,
    },
  )
}
