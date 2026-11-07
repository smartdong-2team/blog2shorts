import { useRef, useState } from 'react'
import { downloadVideo } from '../../api/videos'

export function useVideoDownload() {
  const [downloading, setDownloading] = useState(false)
  const downloadingRef = useRef(false)

  const download = async (url: string) => {
    if (!url || downloadingRef.current) return

    downloadingRef.current = true
    setDownloading(true)

    try {
      const blob = await downloadVideo(url)
      const objectUrl = URL.createObjectURL(blob)

      const link = document.createElement('a')
      link.href = objectUrl
      link.download = 'blog2shorts.mp4'

      document.body.appendChild(link)
      link.click()
      link.remove()

      setTimeout(() => {
        URL.revokeObjectURL(objectUrl)
      }, 60_000)
    } catch (error) {
      console.error('영상 다운로드 실패:', error)
      alert('영상 다운로드에 실패했습니다. 다시 시도해 주세요.')
    } finally {
      downloadingRef.current = false
      setDownloading(false)
    }
  }

  return {
    download,
    downloading,
  }
}