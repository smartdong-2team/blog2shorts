import type { Dispatch } from 'react'
import { Card } from '../../components/common/Card'
import { SegmentedControl, type SegmentItem } from '../../components/common/SegmentedControl'
import { Tabs, type TabItem } from '../../components/common/Tabs'
import { VoiceMusicPicker } from '../audio/VoiceMusicPicker'
import { ExtractResult } from '../content/ExtractResult'
import type { PipelineAction, PipelineState } from '../pipeline/pipelineReducer'
import { SceneList } from './SceneList'
import styles from './EditorWorkspace.module.css'

export const SCENE_EDITOR_ID = 'scene-editor'

export type EditorTab = 'edit' | 'source'

const VIEW_OPTIONS: SegmentItem<'cards' | 'all'>[] = [
  { value: 'cards', label: '카드 보기' },
  { value: 'all', label: '전체 보기' },
]

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
  /** 전체 보기 중인지 */
  bulk: boolean
  onBulkChange: (bulk: boolean) => void
}

/** [편집 | 원문] 탭. 편집 탭은 장면과 음성·음악을 나눠 보여 주고 영상 제작 버튼은 아래 고정 막대(ProgressDock)에 있다 */
export function EditorWorkspace({
  state,
  dispatch,
  locked,
  tab,
  onTabChange,
  bulk,
  onBulkChange,
}: EditorWorkspaceProps) {
  const { scenes, content, audio } = state

  return (
    <Card id={SCENE_EDITOR_ID}>
      <div className={styles.head}>
        <Tabs items={TABS} value={tab} onChange={onTabChange} ariaLabel="편집 영역" />
        {locked && (
          <span className={styles.lockedNote}>
            {state.phase === 'rendering' ? '영상 제작 중' : '대본 만드는 중'}이라 수정할 수 없어요
          </span>
        )}
      </div>

      {tab === 'source' && content ? (
        <ExtractResult content={content} scenes={scenes} />
      ) : (
        <>
          <section className={styles.section}>
            <div className={styles.sectionHead}>
              <h3 className={styles.sectionTitle}>장면</h3>
              {/* 전체 보기: 자막 카드 대신 대본·사진을 한 화면에 모아 보고 고친다. 제작 중에도 보기는 된다 */}
              <SegmentedControl
                items={VIEW_OPTIONS}
                value={bulk ? 'all' : 'cards'}
                onChange={(view) => onBulkChange(view === 'all')}
                ariaLabel="장면 보기 방식"
              />
            </div>
            <SceneList
              state={state}
              dispatch={dispatch}
              locked={locked}
              bulk={bulk}
            />
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
