import { useEffect, useRef } from 'react'
import { Button } from '../../components/common/Button'
import { StepCard } from '../../components/common/StepCard'
import { STEP_IDS, STEP_TITLES, type PipelineState } from './pipelineReducer'
import { formatSec, subtitleIssue, subtitlesOf } from './scenes'
import type { StepId } from './types'
import styles from './ProgressDock.module.css'

interface ProgressDockProps {
  state: PipelineState
  stepElapsed: (id: StepId) => number | null
  onRender: () => void
  onCancel: () => void
}

/** 지금 하는 일·경과 시간 한 줄 (화면 읽기 프로그램용) */
function statusLine(state: PipelineState, stepElapsed: (id: StepId) => number | null): string {
  const { phase, steps } = state
  if (phase === 'idle') return '시작 전'

  const total = STEP_IDS.reduce((sum, id) => sum + (stepElapsed(id) ?? 0), 0)
  const running = STEP_IDS.find((id) => steps[id].status === 'running')
  const failed = STEP_IDS.find((id) => steps[id].status === 'error')
  const cancelled = STEP_IDS.some((id) => steps[id].status === 'cancelled')

  if (running) return `${running}단계 ${STEP_TITLES[running]} 진행 중 · 경과 ${formatSec(total)}`
  if (failed) return `${failed}단계 ${STEP_TITLES[failed]}에서 멈췄습니다 · ${steps[failed].error}`
  if (cancelled) return `중지했습니다 · ${formatSec(total)} 진행`
  if (phase === 'done') return `영상을 만들었습니다 · 총 ${formatSec(total)}`
  return `1~3단계 완료 · ${formatSec(total)}`
}

/** 다시 제작용 새로고침 아이콘 */
function RetryIcon() {
  return (
    <svg className={styles.icon} viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        d="M20 12a8 8 0 1 1-2.34-5.66M20 4v5h-5"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

/** 화면 아래 고정 막대: 진행 단계 5칸 + 오른쪽 주 버튼(진행 중엔 중지하기, 아니면 영상 제작) */
export function ProgressDock({ state, stepElapsed, onRender, onCancel }: ProgressDockProps) {
  const ref = useRef<HTMLElement>(null)

  // 막대 실제 높이를 --dock-height 로 남겨 본문 아래 여백·미리보기 높이가 따라가게 한다
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const root = document.documentElement
    const update = () => root.style.setProperty('--dock-height', `${el.offsetHeight}px`)
    update()
    const observer = new ResizeObserver(update)
    observer.observe(el)
    return () => {
      observer.disconnect()
      root.style.removeProperty('--dock-height')
    }
  }, [])

  const { scenes, steps, result, phase } = state
  const message = statusLine(state, stepElapsed)
  const runningStep = STEP_IDS.some((id) => steps[id].status === 'running')
  const busy = phase === 'analyzing' || phase === 'rendering'
  const isRendering = phase === 'rendering'
  const emptyScene = scenes.findIndex((s) => subtitlesOf(s).some((text) => subtitleIssue(text)))
  const again = !isRendering && (result != null || steps[5].status !== 'idle')
  const renderLabel = isRendering ? '영상 제작 중...' : again ? '영상 다시 제작' : '영상 제작'
  const hint = emptyScene >= 0 ? `${emptyScene + 1}번 장면의 자막을 확인해 주세요` : null

  return (
    <footer ref={ref} className={styles.dock}>
      <div className={styles.inner}>
        <div className={styles.progress}>
          <span role="status" aria-live="polite" className={styles.srOnly}>
            {message}
          </span>
          <div className={styles.steps}>
            {STEP_IDS.map((id) => {
              const elapsed = stepElapsed(id)
              return (
                <StepCard
                  key={id}
                  compact
                  step={id}
                  title={STEP_TITLES[id]}
                  message={steps[id].message}
                  status={steps[id].status}
                  meta={elapsed != null ? `${elapsed.toFixed(1)}초` : undefined}
                />
              )
            })}
          </div>
        </div>

        <div className={styles.action}>
          {runningStep ? (
            <Button variant="danger" className={styles.button} onClick={onCancel}>
              중지하기
            </Button>
          ) : (
            <Button
              className={styles.button}
              onClick={onRender}
              loading={isRendering}
              disabled={busy || scenes.length === 0 || emptyScene >= 0}
            >
              {again && <RetryIcon />}
              {renderLabel}
            </Button>
          )}
          {!runningStep && hint && <span className={styles.hint}>{hint}</span>}
        </div>
      </div>
    </footer>
  )
}
