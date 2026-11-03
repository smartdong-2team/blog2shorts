import { useCallback, useEffect, useState } from 'react'
import { getHealth } from '../api/health'
import { ApiError } from '../api/client'
import type { HealthResponse } from '../types/api'

type HealthState =
  | { status: 'loading' }
  | { status: 'ok'; data: HealthResponse }
  | { status: 'error'; message: string }

export function useHealthCheck() {
  const [state, setState] = useState<HealthState>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    getHealth(controller.signal)
      .then((data) => setState({ status: 'ok', data }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        const message = error instanceof ApiError ? error.message : '알 수 없는 오류가 발생했습니다.'
        setState({ status: 'error', message })
      })

    return () => controller.abort()
  }, [attempt])

  const retry = useCallback(() => {
    setState({ status: 'loading' })
    setAttempt((n) => n + 1)
  }, [])

  return { state, retry }
}
