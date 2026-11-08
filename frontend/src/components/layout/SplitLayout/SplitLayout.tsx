import type { ReactNode } from 'react'
import styles from './SplitLayout.module.css'

interface SplitLayoutProps {
  /** 오른쪽 보조 영역 (스크롤해도 따라오는 패널) */
  aside: ReactNode
  asideVisible: boolean
  children: ReactNode
}

/** [본문 | 보조 패널] 2열. 900px 이하에서는 보조 패널이 위로 쌓인다 */
export function SplitLayout({ aside, asideVisible, children }: SplitLayoutProps) {
  return (
    <div className={asideVisible ? `${styles.split} ${styles.withAside}` : styles.split}>
      <div className={styles.main}>{children}</div>
      {asideVisible && <aside className={styles.aside}>{aside}</aside>}
    </div>
  )
}
