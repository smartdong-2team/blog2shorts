import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import styles from './SceneMenu.module.css'

export interface SceneMenuItem {
  label: string
  onSelect: () => void
  disabled?: boolean
  danger?: boolean
  /** 이 항목 앞에 구분선을 넣는다 */
  separated?: boolean
}

interface SceneMenuProps {
  label: string
  items: SceneMenuItem[]
}

/** 장면 머리의 ⋮ 버튼과 펼침 메뉴 */
export function SceneMenu({ label, items }: SceneMenuProps) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const menuId = useId()

  const enabledItems = () =>
    Array.from(rootRef.current?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]:not(:disabled)') ?? [])

  const close = (restoreFocus: boolean) => {
    setOpen(false)
    if (restoreFocus) buttonRef.current?.focus()
  }

  // 열리면 첫 항목에 초점을 두고, 바깥을 누르면 닫는다
  useEffect(() => {
    if (!open) return

    enabledItems()[0]?.focus()

    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    return () => document.removeEventListener('pointerdown', onPointerDown)
  }, [open])

  const onMenuKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const list = enabledItems()
    const current = list.indexOf(document.activeElement as HTMLButtonElement)

    if (event.key === 'Escape') {
      event.preventDefault()
      close(true)
    } else if (event.key === 'Tab') {
      setOpen(false)
    } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      const step = event.key === 'ArrowDown' ? 1 : -1
      list[(current + step + list.length) % list.length]?.focus()
    } else if (event.key === 'Home' || event.key === 'End') {
      event.preventDefault()
      list[event.key === 'Home' ? 0 : list.length - 1]?.focus()
    }
  }

  return (
    <div ref={rootRef} className={styles.root}>
      <button
        ref={buttonRef}
        type="button"
        className={styles.trigger}
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => setOpen((value) => !value)}
      >
        ⋮
      </button>

      {open && (
        <div id={menuId} role="menu" aria-label={label} className={styles.menu} onKeyDown={onMenuKeyDown}>
          {items.map((item) => (
            <div key={item.label} role="none">
              {item.separated && <div role="separator" className={styles.separator} />}
              <button
                type="button"
                role="menuitem"
                tabIndex={-1}
                className={item.danger ? `${styles.item} ${styles.danger}` : styles.item}
                disabled={item.disabled}
                onClick={() => {
                  close(true)
                  item.onSelect()
                }}
              >
                {item.label}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
