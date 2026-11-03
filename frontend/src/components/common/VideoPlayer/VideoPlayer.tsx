import styles from './VideoPlayer.module.css'

interface VideoPlayerProps {
  /** 영상 주소. 없으면 검은 화면만 */
  src: string | null
  label: string
}

/** 9:16 세로 영상 자리 (가로 300px) */
export function VideoPlayer({ src, label }: VideoPlayerProps) {
  if (!src) return <div className={styles.frame} role="img" aria-label={label} />
  return <video className={styles.frame} src={src} controls playsInline aria-label={label} />
}
