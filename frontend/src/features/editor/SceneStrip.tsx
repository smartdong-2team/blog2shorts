import { useRef, useState, type MouseEvent, type PointerEvent, type ReactNode, type RefObject } from 'react'
import styles from './SceneStrip.module.css'

/** 끌어서 넘길 때 무시하는 요소 (입력칸, 장면 손잡이, 메뉴) */
const NO_PAN = 'input, textarea, select, [data-no-pan]'

/** 이만큼 움직여야 클릭이 아니라 끌기로 본다 */
const PAN_THRESHOLD_PX = 5

interface SceneStripProps {
  /** 카드가 들어 있는 가로 목록. 장면 순서 끌기에서도 같이 쓴다 */
  trackRef: RefObject<HTMLDivElement | null>
  /** 장면을 끌 때 놓을 자리 표시 위치 (목록 안쪽 x 좌표) */
  dropLeft?: number | null
  children: ReactNode
}

interface Pan {
  pointerId: number
  x: number
  scrollLeft: number
  moved: boolean
}

/**
 * 자막 카드를 가로로 늘어놓은 목록.
 * 마우스로 카드의 빈 곳이나 썸네일을 잡고 끌면 좌우로 넘긴다. 터치는 브라우저 기본 스크롤을 쓴다.
 */
export function SceneStrip({ trackRef, dropLeft = null, children }: SceneStripProps) {
  const [panning, setPanning] = useState(false)
  const pan = useRef<Pan | null>(null)
  // 끌기가 끝난 직후의 클릭은 버튼(이미지 변경 등)에 전달하지 않는다
  const suppressClick = useRef(false)

  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (event.pointerType !== 'mouse' || event.button !== 0) return
    if ((event.target as Element).closest(NO_PAN)) return

    // 글자가 선택되지 않게 막는다. 버튼 클릭은 그대로 일어난다
    event.preventDefault()
    pan.current = { pointerId: event.pointerId, x: event.clientX, scrollLeft: event.currentTarget.scrollLeft, moved: false }
  }

  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const current = pan.current
    if (!current || current.pointerId !== event.pointerId) return

    const dx = event.clientX - current.x
    if (!current.moved) {
      if (Math.abs(dx) < PAN_THRESHOLD_PX) return
      current.moved = true
      event.currentTarget.setPointerCapture(event.pointerId)
      setPanning(true)
    }
    event.currentTarget.scrollLeft = current.scrollLeft - dx
  }

  const endPan = (event: PointerEvent<HTMLDivElement>) => {
    const current = pan.current
    if (!current || current.pointerId !== event.pointerId) return

    pan.current = null
    if (!current.moved) return

    suppressClick.current = event.type === 'pointerup'
    // 클릭이 오지 않는 경우(목록 밖에서 놓음)에 다음 클릭까지 막지 않도록 바로 푼다
    setTimeout(() => {
      suppressClick.current = false
    }, 0)
    setPanning(false)
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
  }

  const onClickCapture = (event: MouseEvent<HTMLDivElement>) => {
    if (!suppressClick.current) return
    suppressClick.current = false
    event.preventDefault()
    event.stopPropagation()
  }

  return (
    <div
      ref={trackRef}
      className={panning ? `${styles.track} ${styles.panning}` : styles.track}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endPan}
      onPointerCancel={endPan}
      onClickCapture={onClickCapture}
    >
      {children}
      {dropLeft !== null && <span className={styles.drop} style={{ left: dropLeft }} aria-hidden="true" />}
    </div>
  )
}
