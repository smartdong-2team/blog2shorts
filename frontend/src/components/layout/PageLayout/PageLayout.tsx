import type { ReactNode } from 'react'
import styles from './PageLayout.module.css'

interface PageLayoutProps {
  title: string
  description?: string
  children: ReactNode
}

export function PageLayout({ title, description, children }: PageLayoutProps) {
  return (
    <main className={styles.main}>
      <header className={styles.header}>
        <h1 className={styles.title}>{title}</h1>
        {description && <p className={styles.description}>{description}</p>}
      </header>
      <div className={styles.body}>{children}</div>
    </main>
  )
}
