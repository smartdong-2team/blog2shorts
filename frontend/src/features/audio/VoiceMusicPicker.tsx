import { Grid } from '../../components/common/Grid'
import { Range } from '../../components/common/Range'
import { Select } from '../../components/common/Select'
import { Stack } from '../../components/common/Stack'
import { Text } from '../../components/common/Text'
import type { AudioSettings } from '../pipeline/types'
import { NO_MUSIC, VOICE_OPTIONS } from './options'
import { useMusicOptions } from './useMusicOptions'

interface VoiceMusicPickerProps {
  audio: AudioSettings
  onChange: (patch: Partial<AudioSettings>) => void
  locked: boolean
}

/** 4단계 설정: 나레이션 목소리, 배경음악, 음악 크기 */
export function VoiceMusicPicker({ audio, onChange, locked }: VoiceMusicPickerProps) {
  const musicOptions = useMusicOptions()
  const noMusic = audio.music === NO_MUSIC
  const noTracks = musicOptions.length <= 1

  return (
    <Stack gap={10}>
      <Stack gap={4}>
        <Text variant="heading" as="h3">
          음성과 음악
        </Text>
        <Text variant="caption" tone="muted">
          {noTracks
            ? '이 목소리로 나레이션을 읽습니다. 등록된 배경음악 파일이 없어 음악은 선택할 수 없습니다.'
            : '4단계에서 이 목소리로 나레이션을 읽고, 배경음악을 깔아 줍니다.'}
        </Text>
      </Stack>
      <Grid columns={3} compactColumns={1} gap={14}>
        <Select
          label="목소리"
          options={VOICE_OPTIONS}
          value={audio.voice}
          onChange={(voice) => onChange({ voice })}
          disabled={locked}
        />
        <Select
          label="배경음악"
          options={musicOptions}
          value={audio.music}
          onChange={(music) => onChange({ music })}
          disabled={locked || noTracks}
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
