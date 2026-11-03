import { useState, type FormEvent } from 'react'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { SegmentedControl, type SegmentItem } from '../../components/common/SegmentedControl'
import { Stack } from '../../components/common/Stack'
import { Tabs, type TabItem } from '../../components/common/Tabs'
import { Text } from '../../components/common/Text'
import { TextField } from '../../components/common/TextField'
import { SAMPLE_URL } from '../pipeline/mockData'
import type { ContentInput, Mode } from '../pipeline/types'

type InputKind = ContentInput['kind']

const INPUT_TABS: TabItem<InputKind>[] = [
  { value: 'url', label: '블로그 URL' },
  { value: 'text', label: '본문 붙여넣기' },
]

const MODE_ITEMS: SegmentItem<Mode>[] = [
  { value: 'review', label: '장면 확인 후 만들기' },
  { value: 'auto', label: '처음부터 끝까지 자동' },
]

const MODE_HINT: Record<Mode, string> = {
  review: '컨텐츠·대본·장면(1~3단계)까지 만들고 멈춥니다. 장면과 목소리·음악을 확인한 뒤 영상을 만드세요.',
  auto: '1~5단계를 멈추지 않고 영상까지 만듭니다. 완성 후에도 장면을 고쳐 다시 만들 수 있어요.',
}

const START_LABEL: Record<Mode, string> = {
  review: '장면까지 만들기',
  auto: '영상까지 만들기',
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
    <Card>
      <form onSubmit={submit} noValidate>
        <Stack gap={12}>
          <Tabs items={INPUT_TABS} value={kind} onChange={changeKind} ariaLabel="입력 방식" />
          {kind === 'url' ? (
            <Stack direction="row" gap={8} align="start" wrap>
              <TextField
                ariaLabel="블로그 URL"
                placeholder={SAMPLE_URL}
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                error={error ?? undefined}
                disabled={running}
                grow
              />
              <Button variant="ghost" onClick={() => setUrl(SAMPLE_URL)} disabled={running}>
                예시 글 넣기
              </Button>
              <Button type="submit" disabled={running}>
                {START_LABEL[mode]}
              </Button>
            </Stack>
          ) : (
            <Stack gap={8}>
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
              <Stack direction="row">
                <Button type="submit" disabled={running}>
                  {START_LABEL[mode]}
                </Button>
              </Stack>
            </Stack>
          )}
          <Stack direction="row" gap={12} align="center" wrap>
            <Text variant="small" as="span">
              진행 방식
            </Text>
            <SegmentedControl
              items={MODE_ITEMS}
              value={mode}
              onChange={onModeChange}
              ariaLabel="진행 방식"
              disabled={running}
            />
          </Stack>
          <Text variant="caption" tone="muted">
            {MODE_HINT[mode]}
          </Text>
        </Stack>
      </form>
    </Card>
  )
}
