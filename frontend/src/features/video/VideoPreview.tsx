import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { Stack } from '../../components/common/Stack'
import { Text } from '../../components/common/Text'
import { VideoPlayer } from '../../components/common/VideoPlayer'
import { audioSummary } from '../audio/options'
import type { PipelineState } from '../pipeline/pipelineReducer'
import { formatSec } from '../pipeline/scenes'
import { useVideoDownload } from './useVideoDownload'

interface VideoPreviewProps {
  state: PipelineState
  /** 완성 후 장면·음성 설정을 바꿨는지 */
  stale: boolean
}

/** 5단계 결과. 편집 영역 오른쪽에 붙는 완성 영상 */
export function VideoPreview({ state, stale }: VideoPreviewProps) {
  const { result, scenes, audio } = state
  const { download, downloading } = useVideoDownload()
  if (!result) return null

  return (
    <Card title="완성 영상">
      <VideoPlayer src={result.download_url} label="완성 영상 미리보기" />
      <Stack gap={6}>
        <Text variant="small" as="p">
          약 {formatSec(result.duration_sec)} · {result.width}×{result.height} · {scenes.length}장면
        </Text>
        <Text variant="caption" tone="soft">
          {audioSummary(audio)}
        </Text>
        {stale && (
          <Text variant="caption" tone="warn">
            설정이 바뀌었습니다. 영상 다시 제작으로 반영하세요.
          </Text>
        )}
      </Stack>
      <Button
        onClick={() => result.download_url && download(result.download_url)}
        loading={downloading}
        disabled={!result.download_url}
      >
        {downloading ? '다운로드 준비 중...' : 'MP4 다운로드'}
      </Button>
    </Card>
  )
}
