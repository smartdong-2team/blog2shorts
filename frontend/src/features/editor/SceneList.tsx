import { useState, type Dispatch } from 'react'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { Stack } from '../../components/common/Stack'
import { Text } from '../../components/common/Text'
import { VoiceMusicPicker } from '../audio/VoiceMusicPicker'
import type { PipelineAction, PipelineState } from '../pipeline/pipelineReducer'
import { MAX_SCENES, MIN_SCENES, TARGET_MAX_SEC, TARGET_MIN_SEC, estimateSec } from '../pipeline/scenes'
import { ScriptSummary } from '../script/ScriptSummary'
import { ImagePicker } from './ImagePicker'
import { SceneCard } from './SceneCard'
import styles from './SceneList.module.css'

export const SCENE_EDITOR_ID = 'scene-editor'

interface SceneListProps {
  state: PipelineState
  dispatch: Dispatch<PipelineAction>
  /** 진행 중에는 수정 불가 */
  locked: boolean
  sourceVisible: boolean
  onToggleSource: () => void
  onLocate: (assetId: string) => void
  onRender: () => void
}

/** 3단계 결과 확인·수정 + 4단계 음성·음악 설정 + 영상 만들기 */
export function SceneList({ state, dispatch, locked, sourceVisible, onToggleSource, onLocate, onRender }: SceneListProps) {
  const [picking, setPicking] = useState<number | null>(null)
  const { scenes, content, summary, audio, result, hookText } = state

  const imageUrl = (assetId: string | null) => content?.images.find((i) => i.asset_id === assetId)?.url ?? null
  const sec = estimateSec(scenes)
  const inRange = sec >= TARGET_MIN_SEC && sec <= TARGET_MAX_SEC
  const emptyScene = scenes.findIndex((s) => !s.narration.trim())
  const isRendering = state.phase === 'rendering'

  const renderLabel = isRendering
    ? '영상 제작 중...'
    : result || state.steps[5].status !== 'idle'
      ? '영상 다시 만들기'
      : '영상 만들기'

  return (
    <Card
      id={SCENE_EDITOR_ID}
      title={`장면 확인 · ${content?.title ?? ''}`}
      actions={
        content ? (
          <Button variant="ghost" onClick={onToggleSource}>
            {sourceVisible ? '원문 숨기기' : '원문 보기'}
          </Button>
        ) : undefined
      }
    >
      {summary && <ScriptSummary summary={summary} />}

      <Stack direction="row" justify="between" align="center" wrap>
        <Text variant="small" as="span">
          예상 길이{' '}
          <Text variant="small" tone={inRange ? 'accent' : 'warn'} as="span">
            약 {Math.round(sec)}초 {inRange ? '✓' : '· 목표 범위 밖'}
          </Text>{' '}
          <Text variant="caption" tone="muted" as="span">
            (목표 {TARGET_MIN_SEC}~{TARGET_MAX_SEC}초)
          </Text>
        </Text>
        <Text variant="caption" tone="muted" as="span">
          장면 {scenes.length}개 ({MIN_SCENES}~{MAX_SCENES}개)
        </Text>
      </Stack>

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
            onChange={(patch) => dispatch({ type: 'editScene', index, patch })}
            onMove={(delta) => dispatch({ type: 'moveScene', index, delta })}
            onRemove={() => dispatch({ type: 'removeScene', index })}
            onPickImage={() => setPicking(index)}
            onLocate={() => scene.asset_id && onLocate(scene.asset_id)}
          />
        ))}
      </div>

      <Stack direction="row">
        <Button variant="ghost" onClick={() => dispatch({ type: 'addScene' })} disabled={locked || scenes.length >= MAX_SCENES}>
          + 장면 추가
        </Button>
      </Stack>

      <VoiceMusicPicker audio={audio} onChange={(patch) => dispatch({ type: 'audio', patch })} locked={locked} />

      <Stack direction="row" justify="end" align="center" gap={12} wrap>
        {emptyScene >= 0 && (
          <Text variant="caption" tone="danger" as="span">
            {emptyScene + 1}번 장면 나레이션이 비어 있습니다
          </Text>
        )}

        <Button
          onClick={onRender}
          loading={isRendering}
          disabled={locked || isRendering || emptyScene >= 0}
        >
          {renderLabel}
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
    </Card>
  )
}
