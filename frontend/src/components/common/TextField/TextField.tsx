import { useId, type InputHTMLAttributes, type TextareaHTMLAttributes } from 'react'
import styles from './TextField.module.css'

interface BaseProps {
  label?: string
  /** label이 없을 때 스크린리더용 이름 (둘 중 하나는 필수) */
  ariaLabel?: string
  hint?: string
  error?: string
  /** 가로 Stack 안에서 남은 너비를 차지 */
  grow?: boolean
}

type InputProps = BaseProps & { multiline?: false } & Omit<InputHTMLAttributes<HTMLInputElement>, 'aria-label'>
type TextareaProps = BaseProps & { multiline: true } & Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'aria-label'>

export type TextFieldProps = InputProps | TextareaProps

export function TextField(props: TextFieldProps) {
  const { label, ariaLabel, hint, error, grow = false, id, ...rest } = props
  const autoId = useId()
  const fieldId = id ?? autoId
  const messageId = `${fieldId}-message`
  const message = error ?? hint

  const common = {
    id: fieldId,
    'aria-label': label ? undefined : ariaLabel,
    'aria-invalid': error ? true : undefined,
    'aria-describedby': message ? messageId : undefined,
    className: error ? `${styles.field} ${styles.invalid}` : styles.field,
  }

  let control
  if (rest.multiline) {
    const { multiline: _multiline, ...textareaProps } = rest
    control = <textarea {...textareaProps} {...common} />
  } else {
    const { multiline: _multiline, ...inputProps } = rest
    control = <input {...inputProps} {...common} />
  }

  return (
    <div className={grow ? `${styles.wrapper} ${styles.grow}` : styles.wrapper}>
      {label && (
        <label htmlFor={fieldId} className={styles.label}>
          {label}
        </label>
      )}
      {control}
      {message && (
        <p id={messageId} className={error ? styles.error : styles.hint}>
          {message}
        </p>
      )}
    </div>
  )
}
