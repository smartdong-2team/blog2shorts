import { useRef, useState, type Dispatch } from 'react'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { Stack } from '../../components/common/Stack'
import { Text } from '../../components/common/Text'
import { VoiceMusicPicker } from '../audio/VoiceMusicPicker'
import type { PipelineAction, PipelineState } from '../pipeline/pipelineReducer'
import { MAX_SCENES, MIN_SCENES, TARGET_MAX_SEC, TARGET_MIN_SEC, estimateSec, subtitleIssue, subtitlesOf } from '../pipeline/scenes'
import { ScriptSummary } from '../script/ScriptSummary'
import { ImagePicker } from './ImagePicker'
import { SceneCard } from './SceneCard'
import { SceneCarousel } from './SceneCarousel'
import { useSceneReorder } from './useSceneReorder'
import { TextField } from '../../components/common/TextField'

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
  const trackRef = useRef<HTMLDivElement>(null)
  const { dragging, dropLeft, gripProps } = useSceneReorder({
    trackRef,
    locked,
    onReorder: (from, to) => dispatch({ type: 'reorderScene', from, to }),
    onMove: (index, delta) => dispatch({ type: 'moveScene', index, delta }),
  })
  const { scenes, content, summary, audio, result, hookText } = state

  const imageUrl = (assetId: string | null) => content?.images.find((i) => i.asset_id === assetId)?.url ?? null
  const sec = estimateSec(scenes)
  const inRange = sec >= TARGET_MIN_SEC && sec <= TARGET_MAX_SEC
  const emptyScene = scenes.findIndex((s) => subtitlesOf(s).some((text) => subtitleIssue(text)))
  const isRendering = state.phase === 'rendering'

  const renderLabel = isRendering
    ? '영상 제작 중...'
    : result || state.steps[5].status !== 'idle'
      ? '영상 다시 만들기'
      : '영상 만들기'



      // 최종적으로 프론트엔드에서 사용자가 만든 데이터가 잘 들어가는지 확인하기 위한 용도
  // const inspectRenderData = () => {
  //   const payload = {
  //     hookText,
  //     scenes: scenes.map((scene, index) => ({
  //       order: index + 1,
  //       role: scene.role,
  //       narration: scene.narration,
  //       caption: scene.caption,
  //       asset_id: scene.asset_id,
  //       motion: scene.motion,
  //     })),
  //     audio,
  //   }

  //   console.log('최종 영상 제작 데이터:', payload)
  //   console.log(JSON.stringify(payload, null, 2))
  // }

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

      <div>
        <Text variant="small">
          영상 상단 훅 문구
        </Text>

        <TextField
          ariaLabel="영상 상단 훅 문구"
          placeholder="영상 상단에 표시할 훅 문구를 입력해 주세요"
          value={hookText}
          maxLength={40}
          multiline
          rows={2}
          disabled={locked}
          onChange={(event) =>
            dispatch({
              type: 'hookText',
              hookText: event.target.value,
            })
          }
        />

        <Text variant="caption" tone="muted">
          모든 장면에 공통으로 표시되는 문구 · {hookText.length}/40자
        </Text>
      </div>

      <div>
        <Text variant="caption" tone="muted">
          자막을 순서대로 이어 읽어 음성을 만듭니다. Enter로 줄을 나눌 수 있어요(자막 하나에 두 줄까지). ⠿를 끌면 장면 순서가 바뀝니다.
        </Text>
      </div>

      <SceneCarousel count={scenes.length} trackRef={trackRef} dropLeft={dropLeft} reordering={dragging !== null}>
        {scenes.map((scene, index) => (
          <SceneCard
            key={scene.id}
            scene={scene}
            index={index}
            total={scenes.length}
            dragging={dragging === index}
            gripProps={gripProps(index)}
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
            onSplit={(subtitleIndex) =>
              dispatch({
                type: 'splitScene',
                index,
                subtitleIndex,
              })
            }

            onMergePrevious={() =>
              dispatch({
                type: 'mergeScenePrevious',
                index,
              })
            }

          />
        ))}
      </SceneCarousel>

      <Stack direction="row">
        <Button variant="ghost" onClick={() => dispatch({ type: 'addScene' })} disabled={locked || scenes.length >= MAX_SCENES}>
          + 장면 추가
        </Button>
      </Stack>

      <VoiceMusicPicker audio={audio} onChange={(patch) => dispatch({ type: 'audio', patch })} locked={locked} />

      <Stack direction="row" justify="end" align="center" gap={12} wrap>
        {emptyScene >= 0 && (
          <Text variant="caption" tone="danger" as="span">
            {emptyScene + 1}번 장면의 자막을 확인해 주세요
          </Text>
        )}


        {/* <Button
          variant="ghost"
          onClick={inspectRenderData}
          disabled={locked}
        >
          최종 데이터 확인
        </Button> */}
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
