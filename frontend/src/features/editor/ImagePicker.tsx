import type { ChangeEvent } from 'react'
import { Button } from '../../components/common/Button'
import { Dialog } from '../../components/common/Dialog'
import type { ContentImage } from '../pipeline/types'
import styles from './ImagePicker.module.css'

interface ImagePickerProps {
  open: boolean
  images: ContentImage[]
  current: string | null
  onPick: (assetId: string | null) => void
  onUpload: (image: ContentImage) => void
  onClose: () => void
}

let uploadSeq = 0

/** 장면 이미지 고르기: 블로그 이미지 / 내 컴퓨터 이미지 / 이미지 없음 */
export function ImagePicker({ open, images, current, onPick, onUpload, onClose }: ImagePickerProps) {
  // 백엔드 연결 전: 브라우저 안에서만 쓰는 임시 주소로 미리보기
  const upload = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    onUpload({ asset_id: `upload-${++uploadSeq}`, url: URL.createObjectURL(file), alt: file.name })
  }

  return (
    <Dialog
      open={open}
      title="장면 이미지 선택"
      onClose={onClose}
      footer={
        <>
          <label className={styles.upload}>
            내 컴퓨터에서 올리기
            <input type="file" accept="image/*" onChange={upload} className={styles.file} />
          </label>
          <Button variant="ghost" onClick={onClose}>
            닫기
          </Button>
        </>
      }
    >
      <div className={styles.grid}>
        <button
          type="button"
          className={current === null ? `${styles.option} ${styles.selected}` : styles.option}
          onClick={() => onPick(null)}
          aria-pressed={current === null}
        >
          이미지 없음
        </button>
        {images.map((image, i) => (
          <button
            key={image.asset_id}
            type="button"
            className={current === image.asset_id ? `${styles.option} ${styles.selected}` : styles.option}
            onClick={() => onPick(image.asset_id)}
            aria-pressed={current === image.asset_id}
            aria-label={image.alt ?? `이미지 ${i + 1}`}
          >
            <img src={image.url} alt="" />
          </button>
        ))}
      </div>
    </Dialog>
  )
}
