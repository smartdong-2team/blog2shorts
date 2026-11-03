import { useState } from 'react'
import { Button } from '../components/common/Button'
import { Card } from '../components/common/Card'
import { Grid } from '../components/common/Grid'
import { Stack } from '../components/common/Stack'
import { StatusBadge } from '../components/common/StatusBadge'
import { StepCard, type StepStatus } from '../components/common/StepCard'
import { Tabs, type TabItem } from '../components/common/Tabs'
import { Text } from '../components/common/Text'
import { TextField } from '../components/common/TextField'
import { PageLayout } from '../components/layout/PageLayout'
import { useHealthCheck } from '../hooks/useHealthCheck'

type InputMode = 'url' | 'text'

const INPUT_TABS: TabItem<InputMode>[] = [
  { value: 'url', label: '블로그 URL' },
  { value: 'text', label: '본문 붙여넣기' },
]

// 처리 단계 (실제 진행 상태는 기능 구현 단계에서 연결한다)
const STEPS: { title: string; message: string; status: StepStatus }[] = [
  { title: '글 읽기', message: '대기', status: 'idle' },
  { title: '이미지 수집', message: '대기', status: 'idle' },
  { title: '대본 작성', message: '대기', status: 'idle' },
  { title: '음성 (TTS)', message: '장면 수정 후 진행', status: 'idle' },
  { title: '영상 합성', message: '대기', status: 'idle' },
]

export function HomePage() {
  const [mode, setMode] = useState<InputMode>('url')
  const [url, setUrl] = useState('')
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const { state, retry } = useHealthCheck()

  return (
    <PageLayout
      title="블로그 → 숏폼 영상"
      description="블로그 URL이나 본문을 넣으면 AI가 Hook·본문·CTA 대본(4~6장면)을 만들고, 장면을 확인·수정한 뒤 9:16 영상으로 만듭니다."
    >
      <Card>
        <Tabs items={INPUT_TABS} value={mode} onChange={setMode} ariaLabel="입력 방식" />
        {mode === 'url' ? (
          <Stack direction="row" gap={8}>
            <TextField
              ariaLabel="블로그 URL"
              placeholder="https://blog.naver.com/copper567/글번호"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              grow
            />
            <Button disabled>분석하기</Button>
          </Stack>
        ) : (
          <Stack gap={8}>
            <TextField
              ariaLabel="제목 (선택)"
              placeholder="제목 (선택)"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
            <TextField
              multiline
              ariaLabel="블로그 본문"
              placeholder="블로그 본문을 붙여 넣으세요 (200자 이상)"
              value={text}
              onChange={(event) => setText(event.target.value)}
            />
            <Stack direction="row">
              <Button disabled>분석하기</Button>
            </Stack>
          </Stack>
        )}
        <Text variant="caption" tone="muted">
          분석 기능은 준비 중입니다. (개발 계획 2~3단계)
        </Text>
      </Card>

      <Grid columns={5} compactColumns={3}>
        {STEPS.map((step, index) => (
          <StepCard key={step.title} step={index + 1} {...step} />
        ))}
      </Grid>

      <Card
        title="백엔드 연결 상태"
        actions={
          <Button variant="ghost" onClick={retry} loading={state.status === 'loading'}>
            다시 확인
          </Button>
        }
      >
        <Stack direction="row" gap={8} align="center">
          {state.status === 'loading' && <StatusBadge tone="neutral" label="확인 중" />}
          {state.status === 'ok' && <StatusBadge tone="success" label="연결됨" />}
          {state.status === 'error' && <StatusBadge tone="danger" label="연결 실패" />}
          <Text variant="small" tone="muted" as="span">
            {state.status === 'ok' && `환경 ${state.data.app_env} · 버전 ${state.data.version}`}
            {state.status === 'error' && state.message}
          </Text>
        </Stack>
      </Card>
    </PageLayout>
  )
}
