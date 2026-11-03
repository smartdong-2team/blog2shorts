import type { ReactNode } from 'react'
import styles from './Stack.module.css'

export type SpaceToken = 4 | 6 | 8 | 10 | 12 | 14 | 18 | 20 | 40

interface StackProps {
  direction?: 'column' | 'row'
  gap?: SpaceToken
  align?: 'start' | 'center' | 'end' | 'stretch' | 'baseline'
  justify?: 'start' | 'center' | 'end' | 'between'
  wrap?: boolean
  children: ReactNode
}

export function Stack({
  direction = 'column',
  gap = 12,
  align = 'stretch',
  justify = 'start',
  wrap = false,
  children,
}: StackProps) {
  const classNames = [
    styles.stack,
    styles[direction],
    styles[`gap${gap}`],
    styles[`align-${align}`],
    styles[`justify-${justify}`],
    wrap && styles.wrap,
  ]
    .filter(Boolean)
    .join(' ')

  return <div className={classNames}>{children}</div>
}
