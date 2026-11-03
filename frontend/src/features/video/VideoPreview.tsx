import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { Stack } from '../../components/common/Stack'
import { Text } from '../../components/common/Text'
import { VideoPlayer } from '../../components/common/VideoPlayer'
import { audioSummary } from '../audio/options'
import type { PipelineState } from '../pipeline/pipelineReducer'
import { formatSec } from '../pipeline/scenes'
import type { StepId } from '../pipeline/types'

export const RESULT_ID = 'video-result'

const ROLE_LABEL = { hook: 'HOOK', body: '본문', cta: 'CTA' }

interface VideoPreviewProps {
  state: PipelineState
  stepElapsed: (id: StepId) => number | null
  /** 완성 후 장면·음성 설정을 바꿨는지 */
  stale: boolean
  onEdit: () => void
}

/** 5단계 결과. 백엔드 연결 전에는 검은 9:16 화면 */
export function VideoPreview({ state, stepElapsed, stale, onEdit }: VideoPreviewProps) {
  const { result, scenes, audio } = state
  if (!result) return null

  const sum = (ids: StepId[]) => ids.reduce((s, id) => s + (stepElapsed(id) ?? 0), 0)
  const flow = scenes.map((s) => `${ROLE_LABEL[s.role]} ${s.caption || '(제목 없음)'}`).join(' → ')

  return (
    <Card id={RESULT_ID} title="완성 영상">
      <Stack direction="row" gap={20} align="start" wrap>
        <VideoPlayer src={result.download_url} label="완성 영상 미리보기" />
        <Stack gap={10}>
          <Text variant="heading" as="p">
            약 {formatSec(result.duration_sec)} · {result.width}×{result.height} (9:16) · {scenes.length}장면
          </Text>
          <Text variant="small" tone="soft">
            {audioSummary(audio)}
          </Text>
          <Text variant="small" tone="soft">
            {flow}
          </Text>
          <Text variant="caption" tone="muted">
            만드는 데 {formatSec(sum([1, 2, 3, 4, 5]))} · 컨텐츠~장면 {formatSec(sum([1, 2, 3]))} · 음성~영상{' '}
            {formatSec(sum([4, 5]))}
          </Text>
          {stale && (
            <Text variant="caption" tone="warn">
              장면이나 음성 설정이 바뀌었습니다. 위에서 영상 다시 만들기를 누르면 반영됩니다.
            </Text>
          )}
          <Stack direction="row" gap={8} wrap>
            <Button disabled={!result.download_url}>mp4 다운로드</Button>
            <Button variant="ghost" onClick={onEdit}>
              장면 다시 수정하기
            </Button>
          </Stack>
          {!result.download_url && (
            <Text variant="caption" tone="muted">
              영상 재생과 다운로드는 백엔드를 연결하면 열립니다.
            </Text>
          )}
        </Stack>
      </Stack>
    </Card>
  )
}
