import styles from './StepCard.module.css'

export type StepStatus = 'idle' | 'running' | 'done' | 'error' | 'cancelled'

const STATUS_LABEL: Record<StepStatus, string> = {
  idle: '대기',
  running: '진행 중',
  done: '완료',
  error: '실패',
  cancelled: '중지됨',
}

interface StepCardProps {
  step: number
  title: string
  message: string
  status: StepStatus
  /** 소요 시간·비용 등 한 줄 정보 */
  meta?: string
}

export function StepCard({ step, title, message, status, meta }: StepCardProps) {
  return (
    <div className={`${styles.card} ${styles[status]}`} aria-label={`STEP ${step} ${title}: ${STATUS_LABEL[status]}`}>
      <div className={styles.step}>
        STEP {step}
        {status === 'running' && <span className={styles.spinner} aria-hidden="true" />}
        {status === 'done' && (
          <span className={styles.check} aria-hidden="true">
            ✓
          </span>
        )}
      </div>
      <div className={styles.title}>{title}</div>
      <div className={styles.message}>{message}</div>
      {meta && <div className={styles.meta}>{meta}</div>}
    </div>
  )
}
