import { useState, type Dispatch } from 'react'
import { Button } from '../../components/common/Button'
import { Stack } from '../../components/common/Stack'
import { Text } from '../../components/common/Text'
import { TextField } from '../../components/common/TextField'
import type { PipelineAction, PipelineState } from '../pipeline/pipelineReducer'
import { MAX_SCENES, MIN_SCENES, TARGET_MAX_SEC, TARGET_MIN_SEC, estimateSec } from '../pipeline/scenes'
import { ScriptSummary } from '../script/ScriptSummary'
import { ImagePicker } from './ImagePicker'
import { SceneCard } from './SceneCard'
import styles from './SceneList.module.css'

interface SceneListProps {
  state: PipelineState
  dispatch: Dispatch<PipelineAction>
  /** 진행 중에는 수정 불가 */
  locked: boolean
  onLocate: (assetId: string) => void
}

/** 3단계 결과 확인·수정: 요약, 훅 문구, 장면 카드 */
export function SceneList({ state, dispatch, locked, onLocate }: SceneListProps) {
  const [picking, setPicking] = useState<number | null>(null)
  const { scenes, content, summary, hookText } = state

  const imageUrl = (assetId: string | null) => content?.images.find((i) => i.asset_id === assetId)?.url ?? null
  const sec = estimateSec(scenes)
  const inRange = sec >= TARGET_MIN_SEC && sec <= TARGET_MAX_SEC

  return (
    <Stack gap={12}>
      {summary && <ScriptSummary summary={summary} />}

      <Stack direction="row" justify="between" align="center" wrap>
        <Text variant="small" as="span">
          예상 길이{' '}
          <Text variant="small" tone={inRange ? 'accent' : 'warn'} as="span">
            약 {Math.round(sec)}초 {inRange ? '✓' : `· 목표 ${TARGET_MIN_SEC}~${TARGET_MAX_SEC}초 밖`}
          </Text>
        </Text>
        <Text variant="caption" tone="muted" as="span">
          장면 {scenes.length}개
        </Text>
      </Stack>

      <div>
        <Text variant="small">영상 상단 훅 문구</Text>
        <TextField
          ariaLabel="영상 상단 훅 문구"
          placeholder="영상 상단에 표시할 훅 문구를 입력해 주세요"
          value={hookText}
          maxLength={40}
          multiline
          rows={2}
          disabled={locked}
          onChange={(event) => dispatch({ type: 'hookText', hookText: event.target.value })}
        />
        <Text variant="caption" tone="muted">
          {hookText.length}/40자
        </Text>
      </div>

      <div className={styles.sceneList}>
        {scenes.map((scene, index) => (
          <SceneCard
            key={scene.id}
            scene={scene}
            index={index}
            total={scenes.length}
            imageUrl={imageUrl(scene.asset_id)}
            hookText={hookText}
            locked={locked}
            canRemove={scenes.length > MIN_SCENES}
            canSplit={scenes.length < MAX_SCENES}
            onChange={(patch) => dispatch({ type: 'editScene', index, patch })}
            onSubtitlesChange={(subtitles) => dispatch({ type: 'editSubtitles', index, subtitles })}
            onMove={(delta) => dispatch({ type: 'moveScene', index, delta })}
            onRemove={() => dispatch({ type: 'removeScene', index })}
            onPickImage={() => setPicking(index)}
            onLocate={() => scene.asset_id && onLocate(scene.asset_id)}
            onSplit={(subtitleIndex) => dispatch({ type: 'splitScene', index, subtitleIndex })}
            onMergePrevious={() => dispatch({ type: 'mergeScenePrevious', index })}
          />
        ))}
      </div>

      <Stack direction="row">
        <Button variant="ghost" onClick={() => dispatch({ type: 'addScene' })} disabled={locked || scenes.length >= MAX_SCENES}>
          + 장면 추가
        </Button>
      </Stack>

      <ImagePicker
        open={picking !== null}
        images={content?.images ?? []}
        current={picking !== null ? (scenes[picking]?.asset_id ?? null) : null}
        onPick={(assetId) => {
          if (picking !== null) dispatch({ type: 'editScene', index: picking, patch: { asset_id: assetId } })
          setPicking(null)
        }}
        onUpload={(image) => {
          if (picking !== null) dispatch({ type: 'addImage', image, sceneIndex: picking })
          setPicking(null)
        }}
        onClose={() => setPicking(null)}
      />
    </Stack>
  )
}
