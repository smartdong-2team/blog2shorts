export interface HealthResponse {
  status: 'ok'
  app_env: string
  version: string
}

// 백엔드 공통 오류 포맷: { error: { code, message, details } }
export interface ApiErrorBody {
  error: {
    code: string
    message: string
    details?: unknown
  }
}
