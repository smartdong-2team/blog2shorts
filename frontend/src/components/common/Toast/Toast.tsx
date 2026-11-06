import styles from './Toast.module.css'

export interface ToastItem {
  id: number
  message: string
}

interface ToastListProps {
  toasts: ToastItem[]
  onDismiss: (id: number) => void
}

/** 화면 오른쪽 위 오류 알림. 안내를 읽을 수 있도록 직접 닫을 때까지 남는다 */
export function ToastList({ toasts, onDismiss }: ToastListProps) {
  if (toasts.length === 0) return null

  return (
    <div className={styles.list}>
      {toasts.map((toast) => (
        <div key={toast.id} className={styles.toast} role="alert">
          <p className={styles.message}>{toast.message}</p>
          <button
            type="button"
            className={styles.close}
            aria-label="알림 닫기"
            onClick={() => onDismiss(toast.id)}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
