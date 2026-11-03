import type { CSSProperties, ReactNode } from 'react'
import type { SpaceToken } from '../Stack'
import styles from './Grid.module.css'

interface GridProps {
  columns: number
  /** 화면 폭 900px 이하에서의 열 수 */
  compactColumns?: number
  gap?: SpaceToken
  children: ReactNode
}

export function Grid({ columns, compactColumns = 2, gap = 8, children }: GridProps) {
  // 열 수만 CSS 변수로 넘기고, 실제 스타일은 Grid.module.css에서 처리한다
  const vars = {
    '--grid-columns': columns,
    '--grid-compact-columns': compactColumns,
    '--grid-gap': `var(--space-${gap})`,
  } as CSSProperties

  return (
    <div className={styles.grid} style={vars}>
      {children}
    </div>
  )
}
