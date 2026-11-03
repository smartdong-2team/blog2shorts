import { useId, type SelectHTMLAttributes } from 'react'
import styles from './Select.module.css'

export interface SelectOption {
  value: string
  label: string
}

interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'aria-label'> {
  options: SelectOption[]
  label?: string
  /** label이 없을 때 스크린리더용 이름 */
  ariaLabel?: string
}

export function Select({ options, label, ariaLabel, id, ...rest }: SelectProps) {
  const autoId = useId()
  const fieldId = id ?? autoId
  return (
    <div className={styles.wrapper}>
      {label && (
        <label htmlFor={fieldId} className={styles.label}>
          {label}
        </label>
      )}
      <select id={fieldId} aria-label={label ? undefined : ariaLabel} className={styles.field} {...rest}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}
