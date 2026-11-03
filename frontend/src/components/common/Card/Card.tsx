import type { ReactNode } from 'react'
import styles from './Card.module.css'

interface CardProps {
  title?: string
  /** 제목 오른쪽에 놓을 버튼 등 */
  actions?: ReactNode
  children: ReactNode
  /** 스크롤 이동 대상으로 쓸 때 */
  id?: string
}

export function Card({ title, actions, children, id }: CardProps) {
  return (
    <section id={id} className={styles.card}>
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
