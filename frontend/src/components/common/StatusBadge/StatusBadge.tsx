import styles from './StatusBadge.module.css'

export type StatusTone = 'success' | 'danger' | 'neutral'

interface StatusBadgeProps {
  tone: StatusTone
  label: string
}

export function StatusBadge({ tone, label }: StatusBadgeProps) {
  return (
    <span className={`${styles.badge} ${styles[tone]}`} role="status">
      <span className={styles.dot} aria-hidden="true" />
      {label}
    </span>
  )
}
