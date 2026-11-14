import { useState } from 'react'
import { emphasisSegments, layoutHook, subtitleFontSize } from './hookLayout'
import styles from './SceneThumb.module.css'
import type { Motion } from '../../../features/pipeline/types'

interface SceneThumbProps {
  src: string | null
  label?: string
  onClick?: () => void
  disabled?: boolean
  hookText?: string
  subtitle?: string
  motion?: Motion
}

const motionClass: Record<Motion, string> = {
  zoom_in: styles.zoomIn,
  zoom_out: styles.zoomOut,
  pan_left: styles.panLeft,
  pan_right: styles.panRight,
}

export function SceneThumb({
  src,
  label = '이미지 변경',
  onClick,
  disabled = false,
  hookText = '',
  subtitle = '',
  motion,
}: SceneThumbProps) {
  const [playCount, setPlayCount] = useState(0)
  const hook = layoutHook(hookText)

  return (
    <div className={styles.thumb}>
      <button
        type="button"
        className={styles.previewButton}
        onClick={() => setPlayCount(count => count + 1)}
        disabled={!src}
        aria-label="장면 움직임 다시 재생"
      >
        {hook.text && (
          <span className={styles.hookText} style={{ fontSize: hook.fontSize }}>
            {emphasisSegments(hook.lines).map((segments, row) => (
              <span key={row} className={styles.hookLine}>
                {segments.map((segment, index) => (
                  <span key={index} className={segment.emphasized ? styles.hookEmphasis : undefined}>
                    {segment.text}
                  </span>
                ))}
              </span>
            ))}
          </span>
        )}

        <div className={styles.imageArea}>
          {src ? (
            <img
              key={`${src}-${motion}-${playCount}`}
              src={src}
              alt=""
              className={`${styles.image} ${
                motion ? motionClass[motion] : ''
              }`}
            />
          ) : (
            <span className={styles.empty}>이미지 없음</span>
          )}
        </div>

        {subtitle && (
          <span className={styles.subtitle} style={{ fontSize: subtitleFontSize(subtitle) }}>
            {subtitle}
          </span>
        )}
      </button>

      <button
        type="button"
        className={styles.band}
        onClick={onClick}
        disabled={disabled}
        aria-label={label}
      >
        {label}
      </button>
    </div>
  )
}