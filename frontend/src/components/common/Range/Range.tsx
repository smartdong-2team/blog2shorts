import { useId, type InputHTMLAttributes } from 'react'
import styles from './Range.module.css'

interface RangeProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'value'> {
  label: string
  value: number
  /** 값 옆에 붙일 단위 (예: "%") */
  unit?: string
}

/** 라벨·현재 값이 함께 보이는 슬라이더 */
export function Range({ label, value, unit = '', id, ...rest }: RangeProps) {
  const autoId = useId()
  const fieldId = id ?? autoId
  return (
    <div className={styles.wrapper}>
      <div className={styles.head}>
        <label htmlFor={fieldId} className={styles.label}>
          {label}
        </label>
        <output htmlFor={fieldId} className={styles.value}>
          {value}
          {unit}
        </output>
      </div>
      <input id={fieldId} type="range" value={value} className={styles.input} {...rest} />
    </div>
  )
}
