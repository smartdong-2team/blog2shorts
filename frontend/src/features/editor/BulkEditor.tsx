import { useMemo, useState } from 'react'
import { Button } from '../../components/common/Button'
import { RoleBadge } from '../../components/common/RoleBadge'
import { SegmentedControl } from '../../components/common/SegmentedControl'
import { applyScript, parseScript, scenesToScript, scriptIssue, subtitlesOf } from '../pipeline/scenes'
import type { ContentImage, Scene } from '../pipeline/types'
import { ImagePicker } from './ImagePicker'
import styles from './BulkEditor.module.css'

type BulkTab = 'all' | 'images' | 'script'

const TAB_OPTIONS: { value: BulkTab; label: string }[] = [
  { value: 'all', label: '전체' },
  { value: 'images', label: '이미지' },
  { value: 'script', label: '대본' },
]

const IMAGES_NOTE = '이미지를 끌어다 놓거나 ←/→로 순서를 바꿉니다. 대본은 그대로예요'
const SCRIPT_NOTE = '"──" 줄은 장면 구분, 빈 줄은 다음 자막, 줄바꿈은 자막 안 줄바꿈(두 줄까지)'

interface BulkEditorProps {
  /** 제작 중이면 보기만 */
  locked: boolean
  scenes: Scene[]
  images: ContentImage[]
  /** 고친 내용을 바로 장면에 반영 (카드 보기와 같은 장면을 함께 쓴다) */
  onChange: (scenes: Scene[]) => void
  /** 직접 올린 이미지를 원문 이미지 목록에 추가 */
  onUpload: (image: ContentImage) => void
}

/** 전체 보기: 이미지 순서와 대본을 한 화면에서 고친다. 고친 내용은 바로 반영되고, 제작 중에는 보기만 */
export function BulkEditor({ locked, scenes, images, onChange, onUpload }: BulkEditorProps) {
  const [tab, setTab] = useState<BulkTab>('all')
  /** 입력 중인 대본 글. 규칙에 맞을 때만 장면에 반영하고, 틀린 동안에는 마지막으로 맞았던 장면을 유지한다 */
  const [script, setScript] = useState(() => scenesToScript(scenes))
  const [picking, setPicking] = useState<number | null>(null)
  /** 끌고 있는 장면 칸과, 지금 위에 올라가 있는 칸 */
  const [drag, setDrag] = useState<{ from: number; over: number } | null>(null)

  const blocks = useMemo(() => parseScript(script), [script])
  const issue = scriptIssue(blocks)

  const imageUrl = (assetId: string | null) => images.find((image) => image.asset_id === assetId)?.url ?? null
  const imageNumber = (assetId: string | null) => images.findIndex((image) => image.asset_id === assetId) + 1

  const assets = scenes.map((scene) => scene.asset_id)
  /** 장면 순서·대본은 그대로 두고 장면별 이미지만 바꿔 반영 */
  const setAssets = (next: (string | null)[]) =>
    onChange(scenes.map((scene, index) => ({ ...scene, asset_id: next[index] ?? null })))

  const swap = (index: number, other: number) => {
    const next = [...assets]
    ;[next[index], next[other]] = [next[other], next[index]]
    setAssets(next)
  }

  /** 이미지를 from 칸에서 빼서 to 칸에 끼워 넣는다 (사이 이미지는 한 칸씩 밀림) */
  const move = (from: number, to: number) => {
    const next = [...assets]
    const [moved] = next.splice(from, 1)
    next.splice(to, 0, moved)
    setAssets(next)
  }

  const setImage = (index: number, assetId: string | null) =>
    setAssets(assets.map((value, i) => (i === index ? assetId : value)))

  const editScript = (text: string) => {
    setScript(text)
    const next = parseScript(text)
    if (!scriptIssue(next)) onChange(applyScript(scenes, next))
  }

  return (
    <div className={styles.panel}>
      <div className={styles.head}>
        <SegmentedControl items={TAB_OPTIONS} value={tab} onChange={setTab} ariaLabel="전체 보기 항목" />
        {locked && <span className={styles.lockedNote}>제작 중이라 보기만 할 수 있어요</span>}
      </div>
      {/* 전체: 이미지 먼저, 아래에 대본 */}
      {tab !== 'script' && (
        <section className={styles.section}>
          {tab === 'all' && <h4 className={styles.sectionTitle}>이미지</h4>}
          {!locked && <p className={styles.note}>{IMAGES_NOTE}</p>}
          <ol className={styles.images}>
            {scenes.map((scene, index) => {
              const assetId = assets[index]
              const url = imageUrl(assetId)
              const number = imageNumber(assetId)
              return (
                <li
                  key={scene.id}
                  className={[
                    styles.item,
                    drag?.from === index && styles.dragging,
                    drag && drag.over === index && drag.from !== index && styles.over,
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  draggable={!locked}
                  onDragStart={(event) => {
                    event.dataTransfer.effectAllowed = 'move'
                    event.dataTransfer.setData('text/plain', String(index))
                    setDrag({ from: index, over: index })
                  }}
                  onDragOver={(event) => {
                    if (!drag) return
                    event.preventDefault()
                    event.dataTransfer.dropEffect = 'move'
                    if (drag.over !== index) setDrag({ ...drag, over: index })
                  }}
                  onDrop={(event) => {
                    event.preventDefault()
                    if (drag && drag.from !== index) move(drag.from, index)
                    setDrag(null)
                  }}
                  onDragEnd={() => setDrag(null)}
                >
                  <RoleBadge role={scene.role} index={index + 1} />
                  <button
                    type="button"
                    className={styles.thumb}
                    onClick={() => setPicking(index)}
                    disabled={locked}
                    aria-label={`${index + 1}번 장면 이미지 변경`}
                  >
                    {url ? (
                      <img src={url} alt="" draggable={false} />
                    ) : (
                      <span className={styles.empty}>이미지 없음</span>
                    )}
                    {number > 0 && <span className={styles.number}>이미지 {number}</span>}
                  </button>
                  <p className={styles.line}>{subtitlesOf(scene)[0]?.split('\n')[0]}</p>
                  {!locked && (
                    <div className={styles.moves}>
                      <Button
                        variant="ghost"
                        onClick={() => swap(index, index - 1)}
                        disabled={index === 0}
                        aria-label={`${index + 1}번 장면 이미지를 앞 장면과 바꾸기`}
                      >
                        ←
                      </Button>
                      <Button variant="ghost" onClick={() => setPicking(index)}>
                        변경
                      </Button>
                      <Button
                        variant="ghost"
                        onClick={() => swap(index, index + 1)}
                        disabled={index === scenes.length - 1}
                        aria-label={`${index + 1}번 장면 이미지를 뒤 장면과 바꾸기`}
                      >
                        →
                      </Button>
                    </div>
                  )}
                </li>
              )
            })}
          </ol>
        </section>
      )}

      {tab !== 'images' && (
        <section className={styles.section}>
          {tab === 'all' && <h4 className={styles.sectionTitle}>대본</h4>}
          {!locked && <p className={styles.note}>{SCRIPT_NOTE}</p>}
          <div className={styles.scriptWrap}>
            <textarea
              className={issue ? `${styles.script} ${styles.invalid}` : styles.script}
              value={script}
              onChange={(event) => editScript(event.target.value)}
              aria-label="전체 대본"
              readOnly={locked}
              aria-invalid={issue ? true : undefined}
              spellCheck={false}
            />
            <p className={issue ? styles.error : styles.count} role={issue ? 'alert' : undefined}>
              {issue
                ? `${issue} — 고칠 때까지 영상에는 마지막으로 맞았던 대본이 쓰여요`
                : `장면 ${blocks.length}개 · 자막 ${blocks.reduce((sum, list) => sum + list.length, 0)}개 · 고친 내용은 바로 반영돼요`}
            </p>
          </div>
        </section>
      )}

      <ImagePicker
        open={picking !== null}
        images={images}
        current={picking !== null ? (assets[picking] ?? null) : null}
        onPick={(assetId) => {
          if (picking !== null) setImage(picking, assetId)
          setPicking(null)
        }}
        onUpload={(image) => {
          onUpload(image)
          if (picking !== null) setImage(picking, image.asset_id)
          setPicking(null)
        }}
        onClose={() => setPicking(null)}
      />
    </div>
  )
}
