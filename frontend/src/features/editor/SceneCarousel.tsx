import { useCallback, useEffect, useRef, useState, type PointerEvent, type ReactNode, type RefObject } from 'react'
import styles from './SceneCarousel.module.css'
import { sceneCards } from './sceneCards'

/** 빈 곳을 끌어 넘길 때 무시하는 요소 (입력, 버튼, 장면 손잡이) */
const NO_PAN = 'button, a, input, textarea, select, [data-no-pan]'

interface SceneCarouselProps {
  count: number
  /** 카드가 들어 있는 가로 목록. 장면 순서 끌기에서도 같이 쓴다 */
  trackRef: RefObject<HTMLDivElement | null>
  children: ReactNode
}

interface View {
  first: number
  last: number
}

/** 장면 카드를 좌우 버튼, 끌기, 위치 표시로 넘겨 보는 가로 목록 */
export function SceneCarousel({ count, trackRef, children }: SceneCarouselProps) {
  const [view, setView] = useState<View>({ first: 0, last: 0 })
  const [panning, setPanning] = useState(false)
  const pan = useRef<{ x: number; scrollLeft: number } | null>(null)

  // 카드 중심이 보이는 범위 안에 있으면 보이는 장면으로 센다
  const measure = useCallback(() => {
    const track = trackRef.current
    if (!track) return

    const cards = sceneCards(track)
    const left = track.scrollLeft
    const right = left + track.clientWidth
    const centers = cards.map((card) => card.offsetLeft + card.offsetWidth / 2)
    const first = Math.max(0, centers.findIndex((center) => center >= left))
    const visible = centers.filter((center) => center >= left && center <= right).length

    setView({ first, last: Math.min(cards.length - 1, first + Math.max(visible, 1) - 1) })
  }, [trackRef])

  useEffect(() => {
    const track = trackRef.current
    if (!track) return

    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(track)
    track.addEventListener('scroll', measure, { passive: true })

    return () => {
      observer.disconnect()
      track.removeEventListener('scroll', measure)
    }
  }, [trackRef, measure, count])

  const scrollToCard = (index: number) => {
    const track = trackRef.current
    if (!track) return

    const cards = sceneCards(track)
    const card = cards[Math.max(0, Math.min(index, cards.length - 1))]
    if (!card || !cards[0]) return

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    track.scrollTo({ left: card.offsetLeft - cards[0].offsetLeft, behavior: reduceMotion ? 'auto' : 'smooth' })
  }

  // 마우스로 빈 곳을 잡고 끌면 좌우로 넘긴다. 터치는 브라우저 기본 스크롤을 쓴다
  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (event.pointerType !== 'mouse' || event.button !== 0) return
    if ((event.target as Element).closest(NO_PAN)) return

    event.preventDefault()
    event.currentTarget.setPointerCapture(event.pointerId)
    pan.current = { x: event.clientX, scrollLeft: event.currentTarget.scrollLeft }
    setPanning(true)
  }

  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!pan.current) return
    event.currentTarget.scrollLeft = pan.current.scrollLeft - (event.clientX - pan.current.x)
  }

  const endPan = (event: PointerEvent<HTMLDivElement>) => {
    if (!pan.current) return

    pan.current = null
    setPanning(false)
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
  }

  const atStart = view.first <= 0
  const atEnd = view.last >= count - 1

  return (
    <div className={styles.carousel}>
      <div className={styles.strip}>
        <button
          type="button"
          className={`${styles.nav} ${styles.prev}`}
          onClick={() => scrollToCard(view.first - 1)}
          disabled={atStart}
          aria-label="이전 장면"
        >
          ‹
        </button>

        <div
          ref={trackRef}
          className={panning ? `${styles.track} ${styles.panning}` : styles.track}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={endPan}
          onPointerCancel={endPan}
        >
          {children}
        </div>

        <button
          type="button"
          className={`${styles.nav} ${styles.next}`}
          onClick={() => scrollToCard(view.first + 1)}
          disabled={atEnd}
          aria-label="다음 장면"
        >
          ›
        </button>
      </div>

      <div className={styles.pager}>
        <span className={styles.position} aria-live="polite">
          <strong>{view.first + 1}</strong>
          {view.last > view.first && `~${view.last + 1}`} / {count} 장면
        </span>
        <span className={styles.dots}>
          {Array.from({ length: count }, (_, index) => (
            <button
              key={index}
              type="button"
              className={index >= view.first && index <= view.last ? `${styles.dot} ${styles.dotOn}` : styles.dot}
              onClick={() => scrollToCard(index)}
              aria-label={`장면 ${index + 1}로 이동`}
            />
          ))}
        </span>
      </div>
    </div>
  )
}
