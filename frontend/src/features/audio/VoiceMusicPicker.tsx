import { Grid } from '../../components/common/Grid'
import { Range } from '../../components/common/Range'
import { Select } from '../../components/common/Select'
import { Stack } from '../../components/common/Stack'
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
