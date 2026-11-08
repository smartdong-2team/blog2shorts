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
    <div className={styles.scene}>
      <SceneThumb
        src={imageUrl}
        hookText={hookText}
        subtitle={subtitles[Math.min(active, subtitles.length - 1)]}
        onClick={onPickImage}
        disabled={locked}
        motion={scene.motion}
        label={`장면 ${number} 이미지 변경`}
      />
      <div className={styles.fields}>
        <div className={styles.top}>
          <RoleBadge role={scene.role} index={number} />
          <TextField
            ariaLabel={`장면 ${number} 화면 제목`}
            placeholder="화면 상단 제목 (12자 안팎)"
            maxLength={20}
            value={scene.caption}
            onChange={(event) => onChange({ caption: event.target.value })}
            disabled={locked}
            grow
          />
          <Select
            ariaLabel={`장면 ${number} 움직임`}
            options={MOTION_OPTIONS}
            value={scene.motion}
            onChange={(motion) => onChange({ motion: motion as Motion })}
            disabled={locked}
          />
        </div>

        <div className={styles.subtitles}>
          {subtitles.map((text, position) => (
            <div key={position} className={styles.subtitle}>
              <div className={styles.subtitleHead}>
                <Text variant="small" as="span">
                  자막 {position + 1}
                </Text>
                <div className={styles.subtitleTools}>
                  {position > 0 && (
                    <Button
                      variant="ghost"
                      onClick={() => onSplit(position)}
                      disabled={locked || !canSplit}
                      title="이 자막부터 새 장면으로 나눕니다"
                    >
                      여기서 장면 나누기
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    aria-label={`장면 ${number} 자막 ${position + 1} 삭제`}
                    onClick={() => removeSubtitle(position)}
                    disabled={locked || subtitles.length <= 1}
                  >
                    삭제
                  </Button>
                </div>
              </div>
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
          ))}
        </div>

        <div className={styles.subtitleFooter}>
          <Button variant="ghost" onClick={addSubtitle} disabled={locked}>
            + 자막 추가
          </Button>
          <Text variant="caption" tone="muted" as="span">
            {chars}자 · 약 {narrationSec(scene.narration).toFixed(1)}초
          </Text>
        </div>
      </div>
      <div className={styles.tools}>
        <Button variant="icon" aria-label={`장면 ${number} 위로`} onClick={() => onMove(-1)} disabled={locked || index === 0}>
          ←
        </Button>
        <Button
          variant="icon"
          aria-label={`장면 ${number} 아래로`}
          onClick={() => onMove(1)}
          disabled={locked || index === total - 1}
        >
          →
        </Button>
        <Button variant="icon" onClick={onRemove} disabled={locked || !canRemove}>
          삭제
        </Button>
        <Button variant="icon" onClick={onLocate} disabled={!scene.asset_id} title="원문에서 이 장면 이미지 위치 보기">
          원문
        </Button>
      </div>
    </div>
  )
}
