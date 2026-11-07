import { useEffect, useState } from 'react'
import { Button } from '../components/common/Button'
import { Card } from '../components/common/Card'
import { Grid } from '../components/common/Grid'
import { Stack } from '../components/common/Stack'
import { StatusBadge } from '../components/common/StatusBadge'
import { StepCard } from '../components/common/StepCard'
import { Text } from '../components/common/Text'
import { ToastList } from '../components/common/Toast'
import { PageLayout } from '../components/layout/PageLayout'
import { SplitLayout } from '../components/layout/SplitLayout'
import { ContentInputForm } from '../features/content/ContentInputForm'
import { ExtractResult } from '../features/content/ExtractResult'
import { SCENE_EDITOR_ID, SceneList } from '../features/editor/SceneList'
import { STEP_IDS, STEP_TITLES } from '../features/pipeline/pipelineReducer'
import { usePipeline } from '../features/pipeline/usePipeline'
import { RESULT_ID, VideoPreview } from '../features/video/VideoPreview'
import { RenderStatus } from '../features/video/RenderStatus'
import { useHealthCheck } from '../hooks/useHealthCheck'
import { useToast } from '../hooks/useToast'
import { scrollToElement } from '../utils/scroll'

export function HomePage() {
  const { toasts, showToast, dismissToast, clearToasts } = useToast()
  const { state, dispatch, running, start, render, cancel, stepElapsed, stale } = usePipeline({
    onError: showToast,
    onRunStart: clearToasts,
  })
  const [sourceVisible, setSourceVisible] = useState(false)
  const [highlight, setHighlight] = useState<{ assetId: string; n: number } | null>(null)
  const { state: health, retry } = useHealthCheck()

  // 영상이 완성되면 결과로 이동
  useEffect(() => {
    if (state.phase === 'done') scrollToElement(document.getElementById(RESULT_ID))
  }, [state.phase])

  const locate = (assetId: string) => {
    setSourceVisible(true)
    setHighlight((prev) => ({ assetId, n: (prev?.n ?? 0) + 1 }))
  }

  return (
    <PageLayout
      title="블로그 → 숏폼 영상"
      description="블로그 URL이나 본문을 넣으면 대본과 장면(HOOK·본문·CTA 4~6개)을 만들고, 목소리와 배경음악을 입혀 9:16 영상으로 만듭니다."
    >
      <ToastList toasts={toasts} onDismiss={dismissToast} />

      <ContentInputForm
        mode={state.mode}
        onModeChange={(mode) => dispatch({ type: 'setMode', mode })}
        onStart={(input) => {
          setHighlight(null)
          start(input)
        }}
        running={running}
      />

      <RenderStatus phase={state.phase} steps={state.steps} stepElapsed={stepElapsed} onCancel={cancel} />


      <Grid columns={5} compactColumns={3}>
        {STEP_IDS.map((id) => {
          const elapsed = stepElapsed(id)
          return (
            <StepCard
              key={id}
              step={id}
              title={STEP_TITLES[id]}
              message={state.steps[id].message}
              status={state.steps[id].status}
              meta={elapsed != null ? `${elapsed.toFixed(1)}초` : undefined}
            />
          )
        })}
      </Grid>

      {state.content && (
        <SplitLayout
          asideVisible={sourceVisible}
          aside={<ExtractResult content={state.content} scenes={state.scenes} highlight={highlight} />}
        >
          {state.scenes.length > 0 ? (
            <SceneList
              state={state}
              dispatch={dispatch}
              locked={running}
              sourceVisible={sourceVisible}
              onToggleSource={() => setSourceVisible((v) => !v)}
              onLocate={locate}
              onRender={render}
            />
          ) : (
            <Card title="장면 확인">
              <Text variant="small" tone="muted">
                {running ? '대본과 장면을 만드는 중입니다.' : '장면을 만들기 전에 멈췄습니다. 위에서 다시 시작하세요.'}
              </Text>
            </Card>
          )}
        </SplitLayout>
      )}

      <VideoPreview
        state={state}
        stepElapsed={stepElapsed}
        stale={stale}
        onEdit={() => scrollToElement(document.getElementById(SCENE_EDITOR_ID))}
      />

      <Card
        title="백엔드 연결 상태"
        actions={
          <Button variant="ghost" onClick={retry} loading={health.status === 'loading'}>
            다시 확인
          </Button>
        }
      >
        <Stack direction="row" gap={8} align="center">
          {health.status === 'loading' && <StatusBadge tone="neutral" label="확인 중" />}
          {health.status === 'ok' && <StatusBadge tone="success" label="연결됨" />}
          {health.status === 'error' && <StatusBadge tone="danger" label="연결 실패" />}
          <Text variant="small" tone="muted" as="span">
            {health.status === 'ok' && `환경 ${health.data.app_env} · 버전 ${health.data.version}`}
            {health.status === 'error' && `${health.message} · 지금 화면은 목업 데이터로 동작합니다.`}
          </Text>
        </Stack>
      </Card>
    </PageLayout>
  )
}
