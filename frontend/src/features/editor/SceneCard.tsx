import { useState } from 'react'
import { Button } from '../../components/common/Button'
import { RoleBadge } from '../../components/common/RoleBadge'
import { SceneThumb } from '../../components/common/SceneThumb'
import { Select } from '../../components/common/Select'
import { Text } from '../../components/common/Text'
import { TextField } from '../../components/common/TextField'
import { MOTION_OPTIONS, narrationSec, subtitleIssue, subtitlesOf } from '../pipeline/scenes'
import type { Motion, Scene } from '../pipeline/types'
import styles from './SceneCard.module.css'
import { SceneMenu } from './SceneMenu'

interface SceneCardProps {
  scene: Scene
  index: number
  total: number
  imageUrl: string | null
  hookText: string
  locked: boolean
  canRemove: boolean
  canSplit: boolean
  onChange: (patch: Partial<Pick<Scene, 'caption' | 'motion'>>) => void
  onSubtitlesChange: (subtitles: string[]) => void
  onMove: (delta: -1 | 1) => void
  onRemove: () => void
  onPickImage: () => void
  onLocate: () => void
  onSplit: (subtitleIndex: number) => void
  onMergePrevious: () => void
}

export function SceneCard({
  scene,
  index,
  total,
  imageUrl,
  hookText,
  locked,
  canRemove,
  canSplit,
  onChange,
  onSubtitlesChange,
  onMove,
  onRemove,
  onPickImage,
  onLocate,
  onSplit,
  onMergePrevious,
}: SceneCardProps) {
  const [active, setActive] = useState(0)
  const subtitles = subtitlesOf(scene)
  const chars = scene.narration.replace(/\s/g, '').length
  const number = index + 1
  // 선택한 자막부터 나눈다. 첫 자막을 고른 상태면 둘째 자막부터
  const splitAt = Math.min(Math.max(active, 1), subtitles.length - 1)

  const editSubtitle = (position: number, value: string) => {
    onSubtitlesChange(subtitles.map((text, i) => (i === position ? value : text)))
  }

  const addSubtitle = () => {
    onSubtitlesChange([...subtitles, ''])
    setActive(subtitles.length)
  }

  const removeSubtitle = (position: number) => {
    onSubtitlesChange(subtitles.filter((_, i) => i !== position))
    setActive(0)
  }

  return (
    <div className={styles.scene} data-scene-card>
      <div className={styles.head}>
        <RoleBadge role={scene.role} index={number} />
        <Select
          ariaLabel={`장면 ${number} 움직임`}
          options={MOTION_OPTIONS}
          value={scene.motion}
          onChange={(event) => onChange({ motion: event.target.value as Motion })}
          disabled={locked}
        />
        <SceneMenu
          label={`장면 ${number} 메뉴`}
          items={[
            { label: '원문에서 위치 보기', onSelect: onLocate, disabled: !scene.asset_id },
            {
              label: `자막 ${splitAt + 1}부터 장면 나누기`,
              onSelect: () => onSplit(splitAt),
              disabled: locked || !canSplit || subtitles.length < 2,
              separated: true,
            },
            { label: '앞 장면과 합치기', onSelect: onMergePrevious, disabled: locked || index === 0 },
            { label: '앞으로 이동', onSelect: () => onMove(-1), disabled: locked || index === 0, separated: true },
            { label: '뒤로 이동', onSelect: () => onMove(1), disabled: locked || index === total - 1 },
            { label: '장면 삭제', onSelect: onRemove, disabled: locked || !canRemove, danger: true, separated: true },
          ]}
        />
      </div>

      <SceneThumb
        src={imageUrl}
        hookText={hookText}
        subtitle={subtitles[Math.min(active, subtitles.length - 1)]}
        onClick={onPickImage}
        disabled={locked}
        motion={scene.motion}
        label={`장면 ${number} 이미지 변경`}
      />

      <TextField
        ariaLabel={`장면 ${number} 화면 제목`}
        placeholder="화면 상단 제목 (12자 안팎)"
        maxLength={20}
        value={scene.caption}
        onChange={(event) => onChange({ caption: event.target.value })}
        disabled={locked}
      />

      <div className={styles.subtitles}>
        {subtitles.map((text, position) => (
          <div key={position} className={styles.subtitle}>
            <span className={styles.number} aria-hidden="true">
              {position + 1}
            </span>
            <div className={styles.field}>
              <TextField
                multiline
                rows={2}
                wrap="off"
                ariaLabel={`장면 ${number} 자막 ${position + 1}`}
                placeholder={'첫째 줄\n둘째 줄'}
                value={text}
                disabled={locked}
                error={subtitleIssue(text)}
                onFocus={() => setActive(position)}
                onChange={(event) => editSubtitle(position, event.target.value)}
                onKeyDown={(event) => {
                  if (locked || event.nativeEvent.isComposing) return

                  const { selectionStart, selectionEnd } = event.currentTarget

                  // 첫 자막 맨 앞에서 지우면 앞 장면과 합친다
                  if (
                    event.key === 'Backspace' &&
                    position === 0 &&
                    selectionStart === 0 &&
                    selectionEnd === 0 &&
                    index > 0
                  ) {
                    event.preventDefault()
                    onMergePrevious()
                  }
                }}
              />
            </div>
            <button
              type="button"
              className={styles.remove}
              aria-label={`장면 ${number} 자막 ${position + 1} 삭제`}
              title="자막 삭제"
              onClick={() => removeSubtitle(position)}
              disabled={locked || subtitles.length <= 1}
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      <div className={styles.footer}>
        <Button variant="icon" onClick={addSubtitle} disabled={locked}>
          + 자막 추가
        </Button>
        <Text variant="caption" tone="muted" as="span">
          {chars}자 · 약 {narrationSec(scene.narration).toFixed(1)}초
        </Text>
      </div>
    </div>
  )
}
