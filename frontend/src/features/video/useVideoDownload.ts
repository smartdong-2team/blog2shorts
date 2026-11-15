import { useRef, useState } from 'react'
import { downloadVideo } from '../../api/videos'

/** 크롬·엣지의 저장 창 API. TS DOM 타입에 아직 없어 필요한 만큼만 선언 */
type SaveFilePicker = (options: {
  suggestedName: string
  types: { description: string; accept: Record<string, string[]> }[]
}) => Promise<{ createWritable: () => Promise<{ write: (data: Blob) => Promise<void>; close: () => Promise<void> }> }>

const ERROR_MESSAGE = '영상 다운로드에 실패했습니다. 다시 시도해 주세요.'

function saveWithLink(blob: Blob, fileName: string) {
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000)
}

export function useVideoDownload(onError?: (message: string) => void) {
  const [downloading, setDownloading] = useState(false)
  const downloadingRef = useRef(false)

  const download = async (url: string, fileName: string) => {
    if (!url || downloadingRef.current) return

    downloadingRef.current = true
    setDownloading(true)

    try {
      const picker = (window as Window & { showSaveFilePicker?: SaveFilePicker }).showSaveFilePicker
      if (picker) {
        // 저장 창은 클릭 직후에만 열리므로 영상을 받기 전에 띄운다
        const handle = await picker({
          suggestedName: fileName,
          types: [{ description: 'MP4 영상', accept: { 'video/mp4': ['.mp4'] } }],
        })
        const blob = await downloadVideo(url)
        const writable = await handle.createWritable()
        await writable.write(blob)
        await writable.close()
      } else {
        saveWithLink(await downloadVideo(url), fileName)
      }
    } catch (error) {
      // 저장 창에서 취소
      if (error instanceof DOMException && error.name === 'AbortError') return
      console.error('영상 다운로드 실패:', error)
      if (onError) onError(ERROR_MESSAGE)
      else alert(ERROR_MESSAGE)
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
