import type { Dispatch } from 'react'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { Stack } from '../../components/common/Stack'
import { Tabs, type TabItem } from '../../components/common/Tabs'
import { Text } from '../../components/common/Text'
import { VoiceMusicPicker } from '../audio/VoiceMusicPicker'
import { ExtractResult } from '../content/ExtractResult'
import type { PipelineAction, PipelineState } from '../pipeline/pipelineReducer'
import { subtitleIssue, subtitlesOf } from '../pipeline/scenes'
import { SceneList } from './SceneList'
import styles from './EditorWorkspace.module.css'

export const SCENE_EDITOR_ID = 'scene-editor'

export type EditorTab = 'edit' | 'source'

const TABS: TabItem<EditorTab>[] = [
  { value: 'edit', label: '편집' },
  { value: 'source', label: '원문' },
]

interface EditorWorkspaceProps {
  state: PipelineState
  dispatch: Dispatch<PipelineAction>
  locked: boolean
  tab: EditorTab
  onTabChange: (tab: EditorTab) => void
  highlight: { assetId: string; n: number } | null
  onLocate: (assetId: string) => void
  onRender: () => void
}

/** [편집 | 원문] 탭. 편집 탭은 장면과 음성·음악을 나눠 보여 주고 아래에 영상 만들기 버튼 */
export function EditorWorkspace({
  state,
  dispatch,
  locked,
  tab,
  onTabChange,
  highlight,
  onLocate,
  onRender,
}: EditorWorkspaceProps) {
  const { scenes, content, audio, result } = state
  const emptyScene = scenes.findIndex((s) => subtitlesOf(s).some((text) => subtitleIssue(text)))
  const isRendering = state.phase === 'rendering'
  const renderLabel = isRendering
    ? '영상 제작 중...'
    : result || state.steps[5].status !== 'idle'
      ? '영상 다시 만들기'
      : '영상 만들기'

  return (
    <Card id={SCENE_EDITOR_ID}>
      <div className={styles.head}>
        <Tabs items={TABS} value={tab} onChange={onTabChange} ariaLabel="편집 영역" />
        {content?.title && (
          <Text variant="small" tone="muted" as="span">
            {content.title}
          </Text>
        )}
      </div>

      {tab === 'source' && content ? (
        <ExtractResult content={content} scenes={scenes} highlight={highlight} />
      ) : (
        <>
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>장면</h3>
            <SceneList state={state} dispatch={dispatch} locked={locked} onLocate={onLocate} />
          </section>

          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>음성·음악</h3>
            <VoiceMusicPicker audio={audio} onChange={(patch) => dispatch({ type: 'audio', patch })} locked={locked} />
          </section>

          <Stack direction="row" justify="end" align="center" gap={12} wrap>
            {emptyScene >= 0 && (
              <Text variant="caption" tone="danger" as="span">
                {emptyScene + 1}번 장면의 자막을 확인해 주세요
              </Text>
            )}
            <Button onClick={onRender} loading={isRendering} disabled={locked || isRendering || emptyScene >= 0}>
              {renderLabel}
            </Button>
          </Stack>
        </>
      )}
    </Card>
  )
}
