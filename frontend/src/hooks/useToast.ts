import { useCallback, useRef, useState } from 'react'
import type { ToastItem } from '../components/common/Toast'

export function useToast() {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const nextId = useRef(1)

  const showToast = useCallback((message: string) => {
    const id = nextId.current++
    // 같은 문구는 쌓지 않는다
    setToasts((prev) => (prev.some((toast) => toast.message === message) ? prev : [...prev, { id, message }]))
  }, [])

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id))
  }, [])

  const clearToasts = useCallback(() => setToasts([]), [])

  return { toasts, showToast, dismissToast, clearToasts }
}
