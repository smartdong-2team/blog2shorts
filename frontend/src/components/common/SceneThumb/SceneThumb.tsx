import styles from './SceneThumb.module.css'

interface SceneThumbProps {
  src: string | null
  label?: string
  onClick?: () => void
  disabled?: boolean
  hookText?: string
  subtitle?: string
}

export function SceneThumb({
  src,
  label = '이미지 변경',
  onClick,
  disabled = false,
  hookText = '',
  subtitle = '',
}: SceneThumbProps) {
  return (
    <button
      type="button"
      className={styles.thumb}
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
    >
      {hookText && (
        <span className={styles.hookText}>
          {hookText}
        </span>
      )}

      <div className={styles.imageArea}>
        {src ? (
          <img src={src} alt="" className={styles.image} />
        ) : (
          <span className={styles.empty}>이미지 없음</span>
        )}
      </div>

      {subtitle && (
        <span className={styles.subtitle}>
          {subtitle}
        </span>
      )}

      <span className={styles.band}>{label}</span>
    </button>
  )
}