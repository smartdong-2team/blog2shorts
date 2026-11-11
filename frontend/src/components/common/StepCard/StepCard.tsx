import styles from './StepCard.module.css'

export type StepStatus = 'idle' | 'running' | 'waiting' | 'done' | 'error' | 'cancelled'

const STATUS_LABEL: Record<StepStatus, string> = {
  idle: '대기',
  running: '진행 중',
  waiting: '확인 대기',
  done: '완료',
  error: '실패',
  cancelled: '중지됨',
}

/** 지금 진행 중이거나 사용자가 봐야 하는 상태만 오른쪽 위에 배지로 띄운다 */
const SHOW_BADGE: Record<StepStatus, boolean> = {
  idle: false,
  running: true,
  waiting: true,
  done: false,
  error: true,
  cancelled: true,
}

interface StepCardProps {
  step: number
  title: string
  message: string
  status: StepStatus
  /** 소요 시간·비용 등 한 줄 정보 */
  meta?: string
  /** 아래 고정 막대처럼 좁은 자리에 넣을 때 작게 */
  compact?: boolean
}

export function StepCard({ step, title, message, status, meta, compact = false }: StepCardProps) {
  return (
    <div
      className={`${styles.card} ${styles[status]}${compact ? ` ${styles.compact}` : ''}`}
      title={compact ? [title, message, meta].filter(Boolean).join(' · ') : undefined}
      aria-label={`STEP ${step} ${title}: ${STATUS_LABEL[status]}`}
    >
      <div className={styles.step}>
        STEP {step}
        {status === 'done' && !compact && (
          <span className={styles.check} aria-hidden="true">
            ✓
          </span>
        )}
        {/* 작은 카드는 안내 문구를 빼는 대신 모든 상태를 배지로 보여 준다 */}
        {(compact || SHOW_BADGE[status]) && (
          <span className={styles.badge}>
            {status === 'running' && <span className={styles.spinner} aria-hidden="true" />}
            {STATUS_LABEL[status]}
          </span>
        )}
      </div>
      {compact ? (
        <div className={styles.titleRow}>
          <span className={styles.title}>{title}</span>
          {meta && <span className={styles.meta}>{meta}</span>}
        </div>
      ) : (
        <div className={styles.title}>{title}</div>
      )}
      {!compact && <div className={styles.message}>{message}</div>}
      {!compact && meta && <div className={styles.meta}>{meta}</div>}
    </div>
  )
}
