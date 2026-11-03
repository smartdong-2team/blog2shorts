import type { ReactNode } from 'react'
import styles from './Text.module.css'

export type TextVariant = 'title' | 'heading' | 'body' | 'small' | 'caption'
export type TextTone = 'default' | 'muted' | 'soft' | 'accent' | 'danger' | 'warn'

interface TextProps {
  variant?: TextVariant
  tone?: TextTone
  as?: 'p' | 'span' | 'h1' | 'h2' | 'h3' | 'div'
  children: ReactNode
}

export function Text({ variant = 'body', tone = 'default', as: Tag = 'p', children }: TextProps) {
  return <Tag className={`${styles[variant]} ${styles[tone]}`}>{children}</Tag>
}
