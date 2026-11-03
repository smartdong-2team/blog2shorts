import { useRef, type KeyboardEvent } from 'react'
import styles from './SegmentedControl.module.css'

export interface SegmentItem<T extends string> {
  value: T
  label: string
}

interface SegmentedControlProps<T extends string> {
  items: SegmentItem<T>[]
  value: T
  onChange: (value: T) => void
  ariaLabel: string
  disabled?: boolean
}

/** 둘 이상 중 하나를 고르는 붙은 버튼 (예: 진행 방식). 키보드 ←/→로 이동 */
export function SegmentedControl<T extends string>({
  items,
  value,
  onChange,
  ariaLabel,
  disabled = false,
}: SegmentedControlProps<T>) {
  const groupRef = useRef<HTMLDivElement>(null)

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (disabled || (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight')) return
    event.preventDefault()
    const index = items.findIndex((item) => item.value === value)
    const next = (index + (event.key === 'ArrowRight' ? 1 : -1) + items.length) % items.length
    onChange(items[next].value)
    groupRef.current?.querySelectorAll<HTMLButtonElement>('[role="radio"]')[next]?.focus()
  }

  return (
    <div
      ref={groupRef}
      role="radiogroup"
      aria-label={ariaLabel}
      aria-disabled={disabled || undefined}
      className={styles.group}
      onKeyDown={handleKeyDown}
    >
      {items.map((item) => {
        const checked = item.value === value
        return (
          <button
            key={item.value}
            type="button"
            role="radio"
            aria-checked={checked}
            tabIndex={checked ? 0 : -1}
            disabled={disabled}
            className={checked ? `${styles.item} ${styles.checked}` : styles.item}
            onClick={() => onChange(item.value)}
          >
            {item.label}
          </button>
        )
      })}
    </div>
  )
}
