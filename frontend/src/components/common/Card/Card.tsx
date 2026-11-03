import type { ReactNode } from 'react'
import styles from './Card.module.css'

interface CardProps {
  title?: string
  /** 제목 오른쪽에 놓을 버튼 등 */
  actions?: ReactNode
  children: ReactNode
}

export function Card({ title, actions, children }: CardProps) {
  return (
    <section className={styles.card}>
      {(title || actions) && (
        <div className={styles.head}>
          {title && <h2 className={styles.title}>{title}</h2>}
          {actions && <div className={styles.actions}>{actions}</div>}
        </div>
      )}
      {children}
    </section>
  )
}
