import styles from './SceneThumb.module.css'

interface SceneThumbProps {
  /** 이미지 주소. 없으면 대체 배경 */
  src: string | null
  label?: string
  onClick?: () => void
  disabled?: boolean
}

/** 9:16 장면 썸네일. 누르면 이미지 변경 */
export function SceneThumb({ src, label = '이미지 변경', onClick, disabled = false }: SceneThumbProps) {
  return (
    <button type="button" className={styles.thumb} onClick={onClick} disabled={disabled} aria-label={label}>
      {src ? <img src={src} alt="" className={styles.image} /> : <span className={styles.empty}>이미지 없음</span>}
      <span className={styles.band}>{label}</span>
    </button>
  )
}
