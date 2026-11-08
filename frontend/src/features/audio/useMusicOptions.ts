import { useEffect, useState } from 'react'
import { listMusic } from '../../api/audio'
import { MUSIC_OPTIONS, NO_MUSIC } from './options'

const NO_MUSIC_ONLY = MUSIC_OPTIONS.filter((option) => option.value === NO_MUSIC)

/** 서버에 음원 파일이 있는 곡만 선택지로 보여준다 */
export function useMusicOptions() {
  const [options, setOptions] = useState(NO_MUSIC_ONLY)

  useEffect(() => {
    const controller = new AbortController()

    listMusic(controller.signal)
      .then(({ tracks }) => {
        const available = new Set(tracks.map((track) => track.id))
        setOptions(
          MUSIC_OPTIONS.filter(
            (option) => option.value === NO_MUSIC || available.has(option.value),
          ),
        )
      })
      .catch(() => {
        // 목록을 못 가져오면 "배경음악 없음"만 남긴다
      })

    return () => controller.abort()
  }, [])

  return options
}
