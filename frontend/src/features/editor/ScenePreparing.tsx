import { Card } from '../../components/common/Card'
import { STEP_TITLES } from '../pipeline/pipelineReducer'
import type { StepId, StepState } from '../pipeline/types'
import styles from './ScenePreparing.module.css'

/** 장면이 나오기 전 1~2단계에서 각 단계가 하는 일 */
const STEP_DETAIL: Partial<Record<StepId, string>> = {
  1: '블로그에서 본문 글과 사진을 가져와요',
  2: 'AI가 글과 사진을 읽고 장면 4~6개짜리 숏폼 대본을 쓴 뒤, 자막 카드로 나누고 장면마다 사진을 연결해요. 보통 20초 안팎 걸려요',
}

const PREP_STEPS: StepId[] = [1, 2]

interface ScenePreparingProps {
  running: boolean
  steps: Record<StepId, StepState>
  stepElapsed: (id: StepId) => number | null
}

/** 장면이 만들어지기 전 자리: 지금 어느 단계인지와 각 단계가 하는 일을 보여 준다 */
export function ScenePreparing({ running, steps, stepElapsed }: ScenePreparingProps) {
  const failed = PREP_STEPS.find((id) => steps[id].status === 'error')

  return (
    <Card title={running ? '장면을 만들고 있어요' : '장면을 만들기 전에 멈췄어요'}>
      <p className={styles.lead}>
        {running
          ? '아래 두 단계가 끝나면 이 자리에 자막 카드가 나와요. 그때부터 자막·사진·움직임을 고치고 영상을 만들 수 있어요.'
          : failed
            ? `${failed}단계에서 문제가 생겼어요. 위의 버튼으로 다시 시작해 주세요.`
            : '위의 버튼으로 다시 시작해 주세요.'}
      </p>

      <ol className={styles.steps}>
        {PREP_STEPS.map((id) => {
          const step = steps[id]
          const elapsed = stepElapsed(id)
          const detail =
            step.status === 'done'
              ? step.message
              : step.status === 'error'
                ? (step.error ?? '실패')
                : step.status === 'cancelled'
                  ? '중지했어요'
                  : STEP_DETAIL[id]

          return (
            <li key={id} className={`${styles.step} ${styles[step.status]}`}>
              <span className={styles.marker} aria-hidden="true">
                {step.status === 'done' ? '✓' : step.status === 'error' ? '!' : step.status === 'running' ? '' : id}
              </span>
              <div className={styles.body}>
                <div className={styles.titleRow}>
                  <span className={styles.title}>{STEP_TITLES[id]}</span>
                  {elapsed != null && <span className={styles.time}>{elapsed.toFixed(1)}초</span>}
                </div>
                <p className={styles.detail}>{detail}</p>
              </div>
            </li>
          )
        })}
      </ol>
    </Card>
  )
}
