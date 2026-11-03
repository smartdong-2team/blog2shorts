import { useEffect, useRef, type ReactNode } from 'react'
import styles from './Dialog.module.css'

interface DialogProps {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
  /** 아래쪽 버튼 영역 */
  footer?: ReactNode
}

/** <dialog> 기반 모달. Esc·바깥 클릭으로 닫힌다 */
export function Dialog({ open, title, onClose, children, footer }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={ref}
      className={styles.dialog}
      aria-label={title}
      onClose={onClose}
      onClick={(event) => event.target === ref.current && onClose()}
    >
      <div className={styles.body}>
        <h2 className={styles.title}>{title}</h2>
        {children}
        {footer && <div className={styles.footer}>{footer}</div>}
      </div>
    </dialog>
  )
}
