import { useId } from 'react'
import styles from './RadioGroup.module.css'

export interface RadioItem<T extends string> {
  value: T
  label: string
  /** 라벨 옆 짧은 설명 (선택) */
  description?: string
}

interface RadioGroupProps<T extends string> {
  /** 그룹 이름표. 화면에 보인다 */
  label: string
  items: RadioItem<T>[]
  value: T
  onChange: (value: T) => void
  disabled?: boolean
}

/** 이름표가 붙은 라디오 버튼 한 줄 (예: 대본 스타일). 기본 라디오라 키보드 ←/→가 그대로 된다 */
export function RadioGroup<T extends string>({ label, items, value, onChange, disabled = false }: RadioGroupProps<T>) {
  const name = useId()

  return (
    <fieldset className={styles.group} disabled={disabled}>
      <legend className={styles.legend}>{label}</legend>
      <div className={styles.items}>
        {items.map((item) => (
          <label key={item.value} className={styles.item}>
            <input
              type="radio"
              className={styles.input}
              name={name}
              value={item.value}
              checked={item.value === value}
              onChange={() => onChange(item.value)}
            />
            <span className={styles.label}>{item.label}</span>
            {item.description && <span className={styles.description}>{item.description}</span>}
          </label>
        ))}
      </div>
    </fieldset>
  )
}
