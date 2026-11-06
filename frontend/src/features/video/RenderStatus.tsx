import { Button } from '../../components/common/Button'
import { Stack } from '../../components/common/Stack'
import { Text, type TextTone } from '../../components/common/Text'
import { STEP_IDS, STEP_TITLES } from '../pipeline/pipelineReducer'
import { formatSec } from '../pipeline/scenes'
import type { Phase, StepId, StepState } from '../pipeline/types'

interface RenderStatusProps {
  phase: Phase
  steps: Record<StepId, StepState>
  stepElapsed: (id: StepId) => number | null
  onCancel: () => void
}

/** 단계 카드 위 한 줄: 지금 하는 일·경과 시간 + 중지 버튼 */
export function RenderStatus({ phase, steps, stepElapsed, onCancel }: RenderStatusProps) {
  if (phase === 'idle') return null

  const total = STEP_IDS.reduce((sum, id) => sum + (stepElapsed(id) ?? 0), 0)
  const running = STEP_IDS.find((id) => steps[id].status === 'running')
  const failed = STEP_IDS.find((id) => steps[id].status === 'error')
  const cancelled = STEP_IDS.some((id) => steps[id].status === 'cancelled')

  let tone: TextTone = 'default'
  let message: string
  if (running) {
    tone = 'accent'
    message = `${running}단계 ${STEP_TITLES[running]} 진행 중 · 경과 ${formatSec(total)}`
  } else if (failed) {
    tone = 'danger'
    message = `${failed}단계 ${STEP_TITLES[failed]}에서 멈췄습니다 · ${steps[failed].error}`
  } else if (cancelled) {
    tone = 'danger'
    message = `중지했습니다 · ${formatSec(total)} 진행`
  } else if (phase === 'done') {
    message = `영상을 만들었습니다 · 총 ${formatSec(total)}`
  } else {
    message = `1~3단계 완료 · ${formatSec(total)}. 장면과 음성·음악을 확인하고 영상을 만드세요.`
  }

  return (
    <Stack direction="row" justify="between" align="center" gap={12}>
      <div role="status" aria-live="polite">
        <Text variant="small" tone={tone} as="span">
          {message}
        </Text>
      </div>
      {running && (
        <Button variant="danger" onClick={onCancel}>
          중지하기
        </Button>
      )}
    </Stack>
  )
}
