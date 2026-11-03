/** 움직임 줄이기 설정을 지키는 스크롤 이동 */
export function scrollToElement(element: Element | null, block: ScrollLogicalPosition = 'start') {
  if (!element) return
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  element.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block })
}
