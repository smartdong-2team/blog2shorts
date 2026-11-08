import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import styles from './Select.module.css'

export interface SelectOption {
  value: string
  label: string
}

interface SelectProps {
  options: SelectOption[]
  value: string
  onChange: (value: string) => void
  label?: string
  /** label이 없을 때 스크린리더용 이름 */
  ariaLabel?: string
  disabled?: boolean
  id?: string
}

/** 브라우저 기본 드롭다운 대신 쓰는 선택 상자. ↑/↓·Enter·Esc로 조작 */
export function Select({ options, value, onChange, label, ariaLabel, disabled = false, id }: SelectProps) {
  const autoId = useId()
  const fieldId = id ?? autoId
  const labelId = `${fieldId}-label`
  const listId = `${fieldId}-list`
  const rootRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const [open, setOpen] = useState(false)
  const [upward, setUpward] = useState(false)
  const selectedIndex = Math.max(
    0,
    options.findIndex((option) => option.value === value),
  )
  const [active, setActive] = useState(selectedIndex)
  const selected = options.find((option) => option.value === value)

  // 바깥을 누르면 닫기
  useEffect(() => {
    if (!open) return
    const close = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', close)
    return () => document.removeEventListener('pointerdown', close)
  }, [open])

  // 열린 목록에서 고른 항목이 보이게
  useEffect(() => {
    if (!open) return
    listRef.current?.children[active]?.scrollIntoView({ block: 'nearest' })
  }, [open, active])

  useEffect(() => {
    if (disabled) setOpen(false)
  }, [disabled])

  const openList = () => {
    const rect = rootRef.current?.getBoundingClientRect()
    const listHeight = Math.min(options.length * 40 + 12, 280)
    setUpward(rect ? window.innerHeight - rect.bottom < listHeight && rect.top > listHeight : false)
    setActive(selectedIndex)
    setOpen(true)
  }

  const choose = (index: number) => {
    const option = options[index]
    if (option && option.value !== value) onChange(option.value)
    setOpen(false)
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (disabled) return
    const last = options.length - 1
    switch (event.key) {
      case 'ArrowDown':
      case 'ArrowUp': {
        event.preventDefault()
        if (!open) {
          openList()
          return
        }
        const step = event.key === 'ArrowDown' ? 1 : -1
        setActive((index) => Math.min(last, Math.max(0, index + step)))
        return
      }
      case 'Home':
      case 'End':
        if (!open) return
        event.preventDefault()
        setActive(event.key === 'Home' ? 0 : last)
        return
      case 'Enter':
      case ' ':
        event.preventDefault()
        if (open) choose(active)
        else openList()
        return
      case 'Escape':
        if (open) {
          event.preventDefault()
          setOpen(false)
        }
        return
      case 'Tab':
        setOpen(false)
        return
    }
  }

  return (
    <div className={styles.wrapper}>
      {label && (
        <span id={labelId} className={styles.label}>
          {label}
        </span>
      )}
      <div ref={rootRef} className={styles.root}>
        <button
          id={fieldId}
          type="button"
          className={open ? `${styles.trigger} ${styles.open}` : styles.trigger}
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-controls={open ? listId : undefined}
          aria-labelledby={label ? `${labelId} ${fieldId}` : undefined}
          aria-label={label ? undefined : ariaLabel}
          aria-activedescendant={open ? `${fieldId}-option-${active}` : undefined}
          disabled={disabled}
          onClick={() => (open ? setOpen(false) : openList())}
          onKeyDown={handleKeyDown}
        >
          <span className={styles.value}>{selected?.label ?? ''}</span>
          <svg className={styles.chevron} width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
            <path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        {open && (
          <ul
            ref={listRef}
            id={listId}
            role="listbox"
            aria-label={label ?? ariaLabel}
            className={upward ? `${styles.list} ${styles.upward}` : styles.list}
          >
            {options.map((option, index) => {
              const isSelected = option.value === value
              const classNames = [styles.option, index === active && styles.active, isSelected && styles.selected]
                .filter(Boolean)
                .join(' ')
              return (
                <li
                  key={option.value}
                  id={`${fieldId}-option-${index}`}
                  role="option"
                  aria-selected={isSelected}
                  className={classNames}
                  onPointerEnter={() => setActive(index)}
                  onPointerDown={(event) => event.preventDefault()}
                  onClick={() => choose(index)}
                >
                  <span>{option.label}</span>
                  {isSelected && (
                    <svg className={styles.check} width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
                      <path d="m3 7.2 2.6 2.6L11 4.4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
