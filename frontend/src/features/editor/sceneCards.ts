/** 가로 목록 안의 자막 카드. 카드에는 data-scene-card와 장면 번호(data-scene)를 붙인다 */
export function sceneCards(track: HTMLElement): HTMLElement[] {
  return Array.from(track.querySelectorAll<HTMLElement>(':scope > [data-scene-card]'))
}

export interface SceneGroup {
  /** 첫 카드 왼쪽 (목록 안쪽 기준) */
  start: number
  /** 마지막 카드 오른쪽 (목록 안쪽 기준) */
  end: number
  /** 화면 기준 가운데 x */
  center: number
}

/** 장면별로 카드를 묶은 위치. 장면 순서대로 */
export function sceneGroups(track: HTMLElement): SceneGroup[] {
  const groups: SceneGroup[] = []
  const rects: { left: number; right: number }[] = []

  for (const card of sceneCards(track)) {
    const index = Number(card.dataset.scene)
    const rect = card.getBoundingClientRect()
    const start = card.offsetLeft
    const end = card.offsetLeft + card.offsetWidth

    if (!groups[index]) {
      groups[index] = { start, end, center: 0 }
      rects[index] = { left: rect.left, right: rect.right }
    } else {
      groups[index].end = end
      rects[index].right = rect.right
    }
  }

  return groups.map((group, index) => ({ ...group, center: (rects[index].left + rects[index].right) / 2 }))
}
