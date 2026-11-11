import { Fragment, useCallback, useState, type Dispatch } from 'react'
import { Stack } from '../../components/common/Stack'
import { Text } from '../../components/common/Text'
import { TextField } from '../../components/common/TextField'
import type { PipelineAction, PipelineState } from '../pipeline/pipelineReducer'
import { MAX_SCENES, MIN_SCENES, subtitlesOf } from '../pipeline/scenes'
import { ImagePicker } from './ImagePicker'
import { SceneStrip } from './SceneStrip'
import styles from './SceneList.module.css'
import { SubtitleCard } from './SubtitleCard'

interface SceneListProps {
  state: PipelineState
  dispatch: Dispatch<PipelineAction>
  /** 진행 중에는 수정 불가 */
  locked: boolean
  onLocate: (assetId: string) => void
}

/** 3단계 결과 확인·수정: 훅 문구, 자막 카드 */
export function SceneList({ state, dispatch, locked, onLocate }: SceneListProps) {
  /** 이미지를 고르는 중인 장면과, 몇 번째 자막부터 바꿀지 */
  const [picking, setPicking] = useState<{ index: number; subtitleIndex: number } | null>(null)
  /** 새로 생긴 자막 카드. 그려진 뒤 입력칸에 초점을 준다 */
  const [focusTarget, setFocusTarget] = useState<{ index: number; subtitleIndex: number } | null>(null)
  const clearFocusTarget = useCallback(() => setFocusTarget(null), [])
  const { scenes, content, hookText } = state

  const imageUrl = (assetId: string | null) => content?.images.find((i) => i.asset_id === assetId)?.url ?? null

  return (
    <Stack gap={12}>
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

      <SceneStrip>
        {scenes.map((scene, index) => {
          const subtitles = subtitlesOf(scene)
          const isLast = index === scenes.length - 1

          return (
            <Fragment key={scene.id}>
              {/* 새 장면은 CTA 앞에 들어가므로 추가 카드도 그 자리에 둔다 */}
              {isLast && index > 0 && (
                <button
                  type="button"
                  className={styles.addScene}
                  onClick={() => {
                    dispatch({ type: 'addScene' })
                    setFocusTarget({ index, subtitleIndex: 0 })
                  }}
                  disabled={locked || scenes.length >= MAX_SCENES}
                >
                  + 장면 추가
                </button>
              )}
              {subtitles.map((_, subtitleIndex) => (
                <SubtitleCard
                  key={`${scene.id}-${subtitleIndex}`}
                  scene={scene}
                  sceneIndex={index}
                  subtitleIndex={subtitleIndex}
                  imageUrl={imageUrl(scene.asset_id)}
                  hookText={hookText}
                  locked={locked}
                  canRemoveScene={scenes.length > MIN_SCENES}
                  focusRequested={focusTarget?.index === index && focusTarget.subtitleIndex === subtitleIndex}
                  onFocused={clearFocusTarget}
                  onSubtitleChange={(text) =>
                    dispatch({
                      type: 'editSubtitles',
                      index,
                      subtitles: subtitles.map((value, i) => (i === subtitleIndex ? text : value)),
                    })
                  }
                  onAddSubtitle={() => {
                    dispatch({
                      type: 'editSubtitles',
                      index,
                      subtitles: [...subtitles.slice(0, subtitleIndex + 1), '', ...subtitles.slice(subtitleIndex + 1)],
                    })
                    setFocusTarget({ index, subtitleIndex: subtitleIndex + 1 })
                  }}
                  onRemoveSubtitle={() =>
                    dispatch({ type: 'editSubtitles', index, subtitles: subtitles.filter((_, i) => i !== subtitleIndex) })
                  }
                  onSceneChange={(patch) => dispatch({ type: 'editScene', index, patch })}
                  onRemoveScene={() => dispatch({ type: 'removeScene', index })}
                  onPickImage={() => setPicking({ index, subtitleIndex })}
                  onLocate={() => scene.asset_id && onLocate(scene.asset_id)}
                />
              ))}
            </Fragment>
          )
        })}
      </SceneStrip>

      <ImagePicker
        open={picking !== null}
        images={content?.images ?? []}
        current={picking ? (scenes[picking.index]?.asset_id ?? null) : null}
        onPick={(assetId) => {
          if (picking) dispatch({ type: 'setSceneImage', ...picking, assetId })
          setPicking(null)
        }}
        onUpload={(image) => {
          if (picking) dispatch({ type: 'addImage', image, sceneIndex: picking.index, subtitleIndex: picking.subtitleIndex })
          setPicking(null)
        }}
        onClose={() => setPicking(null)}
      />
    </Stack>
  )
}
