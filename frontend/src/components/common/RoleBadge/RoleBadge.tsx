import styles from './RoleBadge.module.css'

export type SceneRole = 'hook' | 'body' | 'cta'

const ROLE_LABEL: Record<SceneRole, string> = {
  hook: 'HOOK',
  body: '본문',
  cta: 'CTA',
}

interface RoleBadgeProps {
  role: SceneRole
  /** 장면 번호 (1부터). 있으면 "#1 HOOK"처럼 표시 */
  index?: number
}

export function RoleBadge({ role, index }: RoleBadgeProps) {
  return (
    <span className={`${styles.badge} ${styles[role]}`}>
      {index != null && `#${index} `}
      {ROLE_LABEL[role]}
    </span>
  )
}
