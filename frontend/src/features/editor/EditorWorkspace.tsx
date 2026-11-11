import type { Dispatch } from 'react'
import { Card } from '../../components/common/Card'
import { Tabs, type TabItem } from '../../components/common/Tabs'
import { Text } from '../../components/common/Text'
import { VoiceMusicPicker } from '../audio/VoiceMusicPicker'
import { ExtractResult } from '../content/ExtractResult'
import type { PipelineAction, PipelineState } from '../pipeline/pipelineReducer'
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
}

/** [편집 | 원문] 탭. 편집 탭은 장면과 음성·음악을 나눠 보여 주고 영상 제작 버튼은 아래 고정 막대(ProgressDock)에 있다 */
export function EditorWorkspace({
  state,
  dispatch,
  locked,
  tab,
  onTabChange,
  highlight,
  onLocate,
}: EditorWorkspaceProps) {
  const { scenes, content, audio } = state

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
        </>
      )}
    </Card>
  )
}
