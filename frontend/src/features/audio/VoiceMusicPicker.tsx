import { Grid } from '../../components/common/Grid'
import { Range } from '../../components/common/Range'
import { Select } from '../../components/common/Select'
import { Stack } from '../../components/common/Stack'
import { Text } from '../../components/common/Text'
import type { AudioSettings } from '../pipeline/types'
import { MUSIC_OPTIONS, VOICE_OPTIONS } from './options'

interface VoiceMusicPickerProps {
  audio: AudioSettings
  onChange: (patch: Partial<AudioSettings>) => void
  locked: boolean
}

/** 4단계 설정: 나레이션 목소리, 배경음악, 음악 크기 */
export function VoiceMusicPicker({ audio, onChange, locked }: VoiceMusicPickerProps) {
  const noMusic = audio.music === 'none'
  return (
    <Stack gap={10}>
      <Stack gap={4}>
        <Text variant="heading" as="h3">
          음성과 음악
        </Text>
        <Text variant="caption" tone="muted">
          4단계에서 이 목소리로 나레이션을 읽고, 배경음악을 깔아 줍니다.
        </Text>
      </Stack>
      <Grid columns={3} compactColumns={1} gap={14}>
        <Select
          label="목소리"
          options={VOICE_OPTIONS}
          value={audio.voice}
          onChange={(event) => onChange({ voice: event.target.value })}
          disabled={locked}
        />
        <Select
          label="배경음악"
          options={MUSIC_OPTIONS}
          value={audio.music}
          onChange={(event) => onChange({ music: event.target.value })}
          disabled={locked}
        />
        <Range
          label="음악 크기"
          unit="%"
          min={0}
          max={100}
          step={5}
          value={audio.music_volume}
          onChange={(event) => onChange({ music_volume: Number(event.target.value) })}
          disabled={locked || noMusic}
        />
      </Grid>
    </Stack>
  )
}
