import { Button } from '../../components/common/Button'
import { RoleBadge } from '../../components/common/RoleBadge'
import { SceneThumb } from '../../components/common/SceneThumb'
import { Select } from '../../components/common/Select'
import { Text } from '../../components/common/Text'
import { TextField } from '../../components/common/TextField'
import { MOTION_OPTIONS, narrationSec } from '../pipeline/scenes'
import type { Motion, Scene } from '../pipeline/types'
import styles from './SceneCard.module.css'

interface SceneCardProps {
  scene: Scene
  index: number
  total: number
  imageUrl: string | null
  locked: boolean
  canRemove: boolean
  onChange: (patch: Partial<Pick<Scene, 'narration' | 'caption' | 'motion'>>) => void
  onMove: (delta: -1 | 1) => void
  onRemove: () => void
  onPickImage: () => void
  onLocate: () => void
}

export function SceneCard({
  scene,
  index,
  total,
  imageUrl,
  locked,
  canRemove,
  onChange,
  onMove,
  onRemove,
  onPickImage,
  onLocate,
}: SceneCardProps) {
  const chars = scene.narration.replace(/\s/g, '').length
  const number = index + 1

  return (
    <div className={styles.scene}>
      <SceneThumb src={imageUrl} onClick={onPickImage} disabled={locked} label={`장면 ${number} 이미지 변경`} />
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
            onChange={(event) => onChange({ motion: event.target.value as Motion })}
            disabled={locked}
          />
        </div>
        <TextField
          multiline
          rows={3}
          ariaLabel={`장면 ${number} 나레이션`}
          placeholder="나레이션 (음성으로 읽히고 하단 자막으로 나옵니다)"
          value={scene.narration}
          onChange={(event) => onChange({ narration: event.target.value })}
          disabled={locked}
          error={scene.narration.trim() ? undefined : '나레이션을 입력해 주세요'}
        />
        <Text variant="caption" tone="muted">
          {chars}자 · 약 {narrationSec(scene.narration).toFixed(1)}초
        </Text>
      </div>
      <div className={styles.tools}>
        <Button variant="icon" aria-label={`장면 ${number} 위로`} onClick={() => onMove(-1)} disabled={locked || index === 0}>
          ↑
        </Button>
        <Button
          variant="icon"
          aria-label={`장면 ${number} 아래로`}
          onClick={() => onMove(1)}
          disabled={locked || index === total - 1}
        >
          ↓
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
