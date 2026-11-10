/** 가로 목록 안의 장면 카드. 카드에는 data-scene-card 속성을 붙인다 */
export function sceneCards(track: HTMLElement): HTMLElement[] {
  return Array.from(track.querySelectorAll<HTMLElement>(':scope > [data-scene-card]'))
}
