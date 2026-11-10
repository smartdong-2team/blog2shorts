import { useEffect, useRef } from 'react'
import { Text } from '../../components/common/Text'
import { scrollToElement } from '../../utils/scroll'
import type { Content, ContentImage, Scene } from '../pipeline/types'
import styles from './ExtractResult.module.css'

interface ExtractResultProps {
  content: Content
  scenes: Scene[]
  /** 강조할 이미지. n이 바뀔 때마다 그 이미지로 다시 스크롤 */
  highlight: { assetId: string; n: number } | null
}

const IMAGE_LINE = /^\[이미지 (\d+)\]$/

/** 가져온 원문. 본문 속 [이미지 N] 자리에 이미지를 넣어 블로그 순서 그대로 보여 준다 */
export function ExtractResult({ content, scenes, highlight }: ExtractResultProps) {
  const figures = useRef(new Map<string, HTMLElement>())

  useEffect(() => {
    if (highlight) scrollToElement(figures.current.get(highlight.assetId) ?? null, 'center')
  }, [highlight])

  const chars = content.text.replace(/\[이미지 \d+\]/g, '').replace(/\s/g, '').length
  const lines = content.text.split('\n').filter((line) => line.trim())
  // 본문에 [이미지 N] 자리가 없으면(블로그 URL 추출) 이미지를 본문 위에 모아 보여 준다
  const inline = lines.some((line) => IMAGE_LINE.test(line))

  const figure = (image: ContentImage, number: number, key: string | number) => {
    const usedIn = scenes.flatMap((s, index) => (s.asset_id === image.asset_id ? [index + 1] : []))
    const classNames = [
      styles.figure,
      usedIn.length === 0 && styles.unused,
      highlight?.assetId === image.asset_id && styles.highlight,
    ]
      .filter(Boolean)
      .join(' ')

    return (
      <figure
        key={key}
        className={classNames}
        ref={(el) => {
          if (el) figures.current.set(image.asset_id, el)
          else figures.current.delete(image.asset_id)
        }}
      >
        <img src={image.url} alt={image.alt ?? `이미지 ${number}`} loading="lazy" />
        <figcaption className={styles.labels}>
          <span className={styles.label}>이미지 {number}</span>
          {usedIn.map((n) => (
            <span key={n} className={`${styles.label} ${styles.used}`}>
              장면 #{n}
            </span>
          ))}
        </figcaption>
      </figure>
    )
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.meta}>
        <Text variant="small" tone="muted" as="span">
          본문 {chars.toLocaleString()}자 · 이미지 {content.images.length}장
        </Text>
        {content.source_url && (
          <a href={content.source_url} target="_blank" rel="noopener noreferrer" className={styles.link}>
            블로그에서 보기 ↗
          </a>
        )}
      </div>
      {!inline && content.images.length > 0 && (
        <div className={styles.gallery}>{content.images.map((image, i) => figure(image, i + 1, `g${i}`))}</div>
      )}
      <div className={styles.body}>
        {lines.map((line, i) => {
          const match = line.match(IMAGE_LINE)
          if (!match) return <p key={i} className={styles.paragraph}>{line}</p>
          const number = Number(match[1])
          const image = content.images[number - 1]
          return image ? figure(image, number, i) : null
        })}
      </div>
    </div>
  )
}
