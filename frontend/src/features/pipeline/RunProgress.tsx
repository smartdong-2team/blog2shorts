import { STEP_IDS, STEP_TITLES, type PipelineState } from './pipelineReducer'
import { formatSec } from './scenes'
import type { StepId } from './types'
import styles from './RunProgress.module.css'

export interface VideoEta {
  /** 0~1 */
  progress: number
  /** 아직 추정이 어려우면 null */
  remainingSec: number | null
}

interface RunProgressProps {
  state: PipelineState
  stepElapsed: (id: StepId) => number | null
  videoEta: VideoEta | null
}

/** 입력칸 바로 아래 한 줄: 지금 단계, 진행률, 남은 시간. 진행 중일 때만 보인다 */
export function RunProgress({ state, stepElapsed, videoEta }: RunProgressProps) {
  const running = STEP_IDS.find((id) => state.steps[id].status === 'running')
  if (!running) return null

  const { message } = state.steps[running]
  const elapsed = stepElapsed(running) ?? 0
  // 영상 작업(4~5단계)은 서버가 진행률을 알려 준다. 그 전에는 얼마나 남았는지 알 수 없어 움직이는 막대로 보여 준다
  const known = running >= 4 && videoEta != null
  const percent = known ? Math.round(videoEta.progress * 100) : null

  let tail: string
  if (known) {
    tail =
      videoEta.remainingSec != null
        ? `${percent}% · 약 ${formatSec(videoEta.remainingSec)} 남음`
        : `${percent}% · 남은 시간 계산 중`
  } else if (running === 2) {
    tail = `${formatSec(elapsed)} 지남 · 보통 20초 안팎`
  } else {
    tail = `${formatSec(elapsed)} 지남`
  }

  return (
    <div className={styles.wrap} role="status" aria-live="polite">
      <div className={styles.text}>
        <span className={styles.step}>
          {running}/5 {STEP_TITLES[running]}
        </span>
        {message && <span className={styles.message}>{message}</span>}
        <span className={styles.tail}>{tail}</span>
      </div>
      <div
        className={known ? styles.track : `${styles.track} ${styles.indeterminate}`}
        role="progressbar"
        aria-label="진행률"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent ?? undefined}
      >
        <span className={styles.bar} style={known ? { width: `${Math.max(2, percent ?? 0)}%` } : undefined} />
      </div>
    </div>
  )
}
