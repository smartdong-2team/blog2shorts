import { useEffect, useRef } from 'react'
import { Button } from '../../components/common/Button'
import { RoleBadge } from '../../components/common/RoleBadge'
import { SceneThumb } from '../../components/common/SceneThumb'
import { Select } from '../../components/common/Select'
import { Text } from '../../components/common/Text'
import { TextField } from '../../components/common/TextField'
import { MOTION_OPTIONS, narrationSec, subtitleIssue, subtitlesOf } from '../pipeline/scenes'
import type { Motion, Scene } from '../pipeline/types'
import { SceneMenu } from './SceneMenu'
import styles from './SubtitleCard.module.css'

interface SubtitleCardProps {
  scene: Scene
  sceneIndex: number
  /** 장면 안에서 몇 번째 자막인지 */
  subtitleIndex: number
  imageUrl: string | null
  hookText: string
  locked: boolean
  canRemoveScene: boolean
  /** 새로 추가한 자막이면 입력칸에 초점을 준다 */
  focusRequested: boolean
  onFocused: () => void
  onSubtitleChange: (text: string) => void
  onAddSubtitle: () => void
  onRemoveSubtitle: () => void
  onSceneChange: (patch: Partial<Pick<Scene, 'caption' | 'motion'>>) => void
  onRemoveScene: () => void
  onPickImage: () => void
  onLocate: () => void
}

/**
 * 자막 하나를 카드 하나로 보여 준다. 같은 장면의 카드는 이미지를 같이 쓴다.
 * 장면에 딸린 설정(움직임, 화면 제목)은 장면의 첫 카드에만 둔다.
 */
export function SubtitleCard({
  scene,
  sceneIndex,
  subtitleIndex,
  imageUrl,
  hookText,
  locked,
  canRemoveScene,
  focusRequested,
  onFocused,
  onSubtitleChange,
  onAddSubtitle,
  onRemoveSubtitle,
  onSceneChange,
  onRemoveScene,
  onPickImage,
  onLocate,
}: SubtitleCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const subtitles = subtitlesOf(scene)
  const text = subtitles[subtitleIndex] ?? ''
  const count = subtitles.length
  const first = subtitleIndex === 0
  const number = sceneIndex + 1
  const name = count > 1 ? `장면 ${number} 자막 ${subtitleIndex + 1}` : `장면 ${number}`

  useEffect(() => {
    if (!focusRequested) return
    const input = cardRef.current?.querySelector('textarea')
    input?.focus({ preventScroll: true })
    cardRef.current?.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' })
    onFocused()
  }, [focusRequested, onFocused])

  return (
    <div
      ref={cardRef}
      className={first ? `${styles.card} ${styles.sceneStart}` : styles.card}
      data-scene-card
      data-scene={sceneIndex}
    >
      <div className={styles.head}>
        <RoleBadge role={scene.role} index={number} />
        {count > 1 && (
          <span className={styles.position} aria-label={`자막 ${count}개 중 ${subtitleIndex + 1}번째`}>
            {subtitleIndex + 1}/{count}
          </span>
        )}
        <SceneMenu
          label={`${name} 메뉴`}
          items={[
            { label: '원문에서 위치 보기', onSelect: onLocate, disabled: !scene.asset_id },
            { label: '이 자막 삭제', onSelect: onRemoveSubtitle, disabled: locked || count <= 1, separated: true },
            { label: '장면 삭제', onSelect: onRemoveScene, disabled: locked || !canRemoveScene, danger: true, separated: true },
          ]}
        />
      </div>

      <SceneThumb
        src={imageUrl}
        hookText={hookText}
        subtitle={text}
        onClick={onPickImage}
        disabled={locked}
        motion={scene.motion}
        label={first ? '이미지 변경' : '여기부터 이미지 변경'}
      />

      {first && (
        <div className={styles.sceneSettings}>
          <TextField
            ariaLabel={`장면 ${number} 화면 제목`}
            placeholder="화면 제목"
            title="화면 상단 제목 (12자 안팎)"
            maxLength={20}
            value={scene.caption}
            onChange={(event) => onSceneChange({ caption: event.target.value })}
            disabled={locked}
            grow
          />
          <Select
            ariaLabel={`장면 ${number} 움직임`}
            options={MOTION_OPTIONS}
            value={scene.motion}
            onChange={(event) => onSceneChange({ motion: event.target.value as Motion })}
            disabled={locked}
          />
        </div>
      )}

      <div className={styles.field}>
        <TextField
          multiline
          rows={2}
          wrap="off"
          ariaLabel={count > 1 ? name : `${name} 자막`}
          placeholder={'첫째 줄\n둘째 줄'}
          value={text}
          disabled={locked}
          error={subtitleIssue(text)}
          onChange={(event) => onSubtitleChange(event.target.value)}
        />
      </div>

      <div className={styles.footer}>
        <Button variant="icon" onClick={onAddSubtitle} disabled={locked} title="이 자막 뒤에 같은 이미지로 자막 추가">
          + 자막
        </Button>
        <Text variant="caption" tone="muted" as="span">
          약 {narrationSec(text).toFixed(1)}초
        </Text>
      </div>
    </div>
  )
}
