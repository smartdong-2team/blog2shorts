import { useId, useRef, useState, type FormEvent } from 'react'
import { Button } from '../../components/common/Button'
import { SegmentedControl, type SegmentItem } from '../../components/common/SegmentedControl'
import { Tabs, type TabItem } from '../../components/common/Tabs'
import { TextField } from '../../components/common/TextField'
import type { ContentInput, Mode } from '../pipeline/types'
import styles from './ContentInputForm.module.css'

type InputKind = ContentInput['kind']

const INPUT_TABS: TabItem<InputKind>[] = [
  { value: 'url', label: '블로그 URL' },
  { value: 'text', label: '본문 붙여넣기' },
]

const MODE_ITEMS: SegmentItem<Mode>[] = [
  { value: 'auto', label: '자동 제작' },
  { value: 'review', label: '검토 후 제작' },
]

const START_LABEL: Record<Mode, string> = {
  auto: '영상 제작',
  review: '장면 만들기',
}

const MIN_TEXT = 200
const BLOG_URL = /^https?:\/\/(m\.)?blog\.naver\.com\/[\w-]+\/\d+/

interface ContentInputFormProps {
  mode: Mode
  onModeChange: (mode: Mode) => void
  onStart: (input: ContentInput) => void
  running: boolean
}

export function ContentInputForm({ mode, onModeChange, onStart, running }: ContentInputFormProps) {
  const [kind, setKind] = useState<InputKind>('url')
  const [url, setUrl] = useState('')
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const urlErrorId = useId()
  const urlRef = useRef<HTMLInputElement>(null)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (kind === 'url') {
      if (!BLOG_URL.test(url.trim())) {
        setError('네이버 블로그 글 주소를 넣어 주세요. 예: https://blog.naver.com/아이디/글번호')
        return
      }
      setError(null)
      onStart({ kind: 'url', url: url.trim() })
      return
    }
    const length = text.trim().length
    if (length < MIN_TEXT) {
      setError(`본문이 ${length}자입니다. ${MIN_TEXT}자 이상 붙여 넣어 주세요.`)
      return
    }
    setError(null)
    onStart({ kind: 'text', title, text })
  }

  const changeKind = (next: InputKind) => {
    setKind(next)
    setError(null)
  }

  return (
    <form className={styles.form} onSubmit={submit} noValidate>
      <div className={styles.toolbar}>
        <Tabs items={INPUT_TABS} value={kind} onChange={changeKind} ariaLabel="입력 방식" />
        <SegmentedControl
          items={MODE_ITEMS}
          value={mode}
          onChange={onModeChange}
          ariaLabel="진행 방식"
          disabled={running}
        />
      </div>

      {kind === 'url' ? (
        <div className={styles.urlField}>
          <div className={error ? `${styles.bar} ${styles.invalid}` : styles.bar}>
            <input
              className={styles.input}
              type="url"
              inputMode="url"
              aria-label="블로그 URL"
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? urlErrorId : undefined}
              placeholder="https://blog.naver.com/아이디/글번호"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              disabled={running}
              ref={urlRef}
            />
            {url && !running && (
              <button
                type="button"
                className={styles.clear}
                aria-label="주소 지우기"
                onClick={() => {
                  setUrl('')
                  setError(null)
                  urlRef.current?.focus()
                }}
              >
                <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
                  <path d="M1 1l8 8M9 1L1 9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                </svg>
              </button>
            )}
            <Button type="submit" className={styles.submit} disabled={running}>
              {START_LABEL[mode]}
            </Button>
          </div>
          {error && (
            <p id={urlErrorId} className={styles.error}>
              {error}
            </p>
          )}
        </div>
      ) : (
        <div className={styles.textFields}>
          <TextField
            ariaLabel="제목 (선택)"
            placeholder="제목 (선택)"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            disabled={running}
          />
          <TextField
            multiline
            ariaLabel="블로그 본문"
            placeholder={`블로그 본문을 붙여 넣으세요 (${MIN_TEXT}자 이상)`}
            value={text}
            onChange={(event) => setText(event.target.value)}
            hint={`${text.trim().length.toLocaleString()}자`}
            error={error ?? undefined}
            disabled={running}
          />
          <div className={styles.textSubmit}>
            <Button type="submit" className={styles.submit} disabled={running}>
              {START_LABEL[mode]}
            </Button>
          </div>
        </div>
      )}
    </form>
  )
}
