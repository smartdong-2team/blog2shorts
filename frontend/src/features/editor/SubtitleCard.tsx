import { useEffect, useRef } from 'react'
import { Button } from '../../components/common/Button'
import { RoleBadge } from '../../components/common/RoleBadge'
import { SceneThumb } from '../../components/common/SceneThumb'
import { Select } from '../../components/common/Select'
import { Text } from '../../components/common/Text'
import { TextField } from '../../components/common/TextField'
import { MOTION_OPTIONS, narrationSec, subtitleIssue, subtitlesOf } from '../pipeline/scenes'
import type { Motion, Scene } from '../pipeline/types'
import styles from './SubtitleCard.module.css'

interface SubtitleCardProps {
  scene: Scene
  sceneIndex: number
  /** 장면 안에서 몇 번째 자막인지 */
  subtitleIndex: number
  imageUrl: string | null
  hookText: string
  locked: boolean
  /** 장면을 지울 수 있는지 (최소 장면 수보다 많을 때) */
  canRemoveScene: boolean
  /** 새로 추가한 자막이면 입력칸에 초점을 준다 */
  focusRequested: boolean
  onFocused: () => void
  onSubtitleChange: (text: string) => void
  onAddSubtitle: () => void
  onRemoveSubtitle: () => void
  onSceneChange: (patch: Partial<Pick<Scene, 'motion'>>) => void
  onRemoveScene: () => void
  onPickImage: () => void
}

/**
 * 자막 하나를 카드 하나로 보여 준다. 같은 장면의 카드는 이미지를 같이 쓴다.
 * 장면에 딸린 설정(움직임)은 장면의 첫 카드에서만 고친다.
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
        {/* 이 자막만 지운다. 장면의 마지막 자막이면 장면이 지워진다 */}
        <button
          type="button"
          className={styles.remove}
          onClick={count > 1 ? onRemoveSubtitle : onRemoveScene}
          disabled={locked || (count <= 1 && !canRemoveScene)}
          aria-label={count > 1 ? `${name} 삭제` : `장면 ${number} 삭제`}
          title={
            count <= 1 && !canRemoveScene ? '장면은 최소 개수보다 줄일 수 없어요' : count > 1 ? '이 자막 삭제' : '장면 삭제'
          }
        >
          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      {/* 장면 설정은 첫 카드에서만 고치고, 나머지 카드는 같은 높이의 빈 자리로 둔다.
          목록 안쪽에서 펼침 목록이 잘리지 않게 썸네일 위에 둔다 */}
      <div className={styles.sceneSettings}>
        <span className={styles.settingLabel}>움직임</span>
        {first ? (
          <Select
            ariaLabel={`장면 ${number} 움직임`}
            options={MOTION_OPTIONS}
            value={scene.motion}
            onChange={(motion) => onSceneChange({ motion: motion as Motion })}
            disabled={locked}
          />
        ) : (
          <span className={styles.settingPlaceholder}>앞 카드와 같음</span>
        )}
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
