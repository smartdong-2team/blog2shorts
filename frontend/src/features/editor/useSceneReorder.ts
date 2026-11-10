import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent, type RefObject } from 'react'
import { sceneCards } from './sceneCards'

/** 목록 가장자리에서 이 거리 안으로 끌면 그쪽으로 넘긴다 */
const EDGE_PX = 56
const EDGE_SCROLL_PX = 14

interface Drag {
  from: number
  /** 끼워 넣을 자리. 0이면 맨 앞, 장면 수와 같으면 맨 뒤 */
  slot: number
  pointerId: number
  x: number
  /** 놓을 자리 표시 위치. 놓아도 그대로인 자리면 null */
  dropLeft: number | null
}

interface Options {
  trackRef: RefObject<HTMLDivElement | null>
  locked: boolean
  onReorder: (from: number, to: number) => void
  onMove: (index: number, delta: -1 | 1) => void
}

/** 포인터 위치가 몇 번째 카드 사이인지 */
function slotAt(track: HTMLElement, clientX: number): number {
  return sceneCards(track).filter((card) => {
    const rect = card.getBoundingClientRect()
    return rect.left + rect.width / 2 < clientX
  }).length
}

/** 끼워 넣을 자리를 표시할 x 좌표 (목록 안쪽 기준) */
function slotLeft(track: HTMLElement, slot: number): number {
  const cards = sceneCards(track)
  const gap = parseFloat(getComputedStyle(track).columnGap) || 0
  const before = cards[slot - 1]
  const after = cards[slot]

  if (after) return after.offsetLeft - gap / 2
  if (before) return before.offsetLeft + before.offsetWidth + gap / 2
  return 0
}

/** 포인터가 x에 있을 때의 끌기 상태 */
function dragAt(track: HTMLElement, current: Omit<Drag, 'slot' | 'dropLeft'>): Drag {
  const slot = slotAt(track, current.x)
  const stays = slot === current.from || slot === current.from + 1
  return { ...current, slot, dropLeft: stays ? null : slotLeft(track, slot) }
}

/**
 * 장면 머리의 ⠿ 손잡이로 장면 순서를 바꾼다.
 * 마우스와 터치는 끌어서 놓고, 키보드는 손잡이에서 ←/→로 한 칸씩 옮긴다.
 */
export function useSceneReorder({ trackRef, locked, onReorder, onMove }: Options) {
  const [drag, setDrag] = useState<Drag | null>(null)
  const dragRef = useRef<Drag | null>(null)

  const active = drag !== null

  const update = (next: Drag | null) => {
    dragRef.current = next
    setDrag(next)
  }

  // 손을 가장자리에 대고 있으면 멈춰 있어도 계속 넘긴다
  useEffect(() => {
    if (!active) return

    let frame = 0
    const tick = () => {
      const track = trackRef.current
      const current = dragRef.current
      if (track && current) {
        const rect = track.getBoundingClientRect()
        const delta =
          current.x < rect.left + EDGE_PX ? -EDGE_SCROLL_PX : current.x > rect.right - EDGE_PX ? EDGE_SCROLL_PX : 0

        if (delta) {
          track.scrollLeft += delta
          const next = dragAt(track, current)
          dragRef.current = next
          setDrag(next)
        }
      }
      frame = requestAnimationFrame(tick)
    }

    frame = requestAnimationFrame(tick)

    // 끄는 중 Esc를 누르면 놓지 않고 취소한다
    const onKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key !== 'Escape') return
      dragRef.current = null
      setDrag(null)
    }
    document.addEventListener('keydown', onKeyDown)

    return () => {
      cancelAnimationFrame(frame)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [active, trackRef])

  const cancel = () => update(null)

  const gripProps = (index: number) => ({
    'data-no-pan': true,
    disabled: locked,
    onPointerDown: (event: PointerEvent<HTMLElement>) => {
      const track = trackRef.current
      if (locked || !track || event.button !== 0) return

      event.preventDefault()
      event.currentTarget.setPointerCapture(event.pointerId)
      update(dragAt(track, { from: index, pointerId: event.pointerId, x: event.clientX }))
    },
    onPointerMove: (event: PointerEvent<HTMLElement>) => {
      const current = dragRef.current
      const track = trackRef.current
      if (!current || !track || current.pointerId !== event.pointerId) return

      update(dragAt(track, { ...current, x: event.clientX }))
    },
    onPointerUp: (event: PointerEvent<HTMLElement>) => {
      const current = dragRef.current
      if (!current || current.pointerId !== event.pointerId) return

      update(null)
      // 제자리(자기 앞뒤 틈)에 놓으면 그대로 둔다
      if (current.slot !== current.from && current.slot !== current.from + 1) {
        onReorder(current.from, current.slot > current.from ? current.slot - 1 : current.slot)
      }
    },
    onPointerCancel: cancel,
    onLostPointerCapture: cancel,
    onKeyDown: (event: KeyboardEvent<HTMLElement>) => {
      if (!locked && (event.key === 'ArrowLeft' || event.key === 'ArrowRight')) {
        event.preventDefault()
        onMove(index, event.key === 'ArrowLeft' ? -1 : 1)
      }
    },
  })

  return {
    /** 끌고 있는 장면 위치 */
    dragging: drag?.from ?? null,
    dropLeft: drag?.dropLeft ?? null,
    gripProps,
  }
}
