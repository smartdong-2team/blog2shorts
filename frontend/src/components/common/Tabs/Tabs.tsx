import { useRef, type KeyboardEvent } from 'react'
import styles from './Tabs.module.css'

export interface TabItem<T extends string> {
  value: T
  label: string
}

interface TabsProps<T extends string> {
  items: TabItem<T>[]
  value: T
  onChange: (value: T) => void
  ariaLabel: string
}

export function Tabs<T extends string>({ items, value, onChange, ariaLabel }: TabsProps<T>) {
  const listRef = useRef<HTMLDivElement>(null)

  // ←/→ 키로 탭 이동
  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
    const index = items.findIndex((item) => item.value === value)
    const step = event.key === 'ArrowRight' ? 1 : -1
    const next = (index + step + items.length) % items.length
    onChange(items[next].value)
    listRef.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus()
  }

  return (
    <div ref={listRef} role="tablist" aria-label={ariaLabel} className={styles.tabs} onKeyDown={handleKeyDown}>
      {items.map((item) => {
        const selected = item.value === value
        return (
          <button
            key={item.value}
            type="button"
            role="tab"
            aria-selected={selected}
            tabIndex={selected ? 0 : -1}
            className={selected ? `${styles.tab} ${styles.selected}` : styles.tab}
            onClick={() => onChange(item.value)}
          >
            {item.label}
          </button>
        )
      })}
    </div>
  )
}
