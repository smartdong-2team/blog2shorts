// 파일 이름에 못 쓰는 문자 + 제어문자
// eslint-disable-next-line no-control-regex
const FORBIDDEN = /[\\/:*?"<>|\u0000-\u001f\u007f]/g
const MAX_WORD = 20

const pad = (n: number) => String(n).padStart(2, '0')

/** 다운로드 기본 이름. 예: 1115_2109_인디자인독학.mp4 */
export function videoFileName(title: string | undefined, now = new Date()): string {
  const stamp = `${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}`
  const word = (title ?? '').replace(FORBIDDEN, ' ').trim().split(/\s+/)[0] ?? ''
  const name = Array.from(word).slice(0, MAX_WORD).join('') || 'blog2shorts'
  return `${stamp}_${name}.mp4`
}
