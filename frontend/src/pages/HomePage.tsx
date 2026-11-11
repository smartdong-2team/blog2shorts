import { useEffect, useState } from 'react'
import { ToastList } from '../components/common/Toast'
import { PageLayout } from '../components/layout/PageLayout'
import { SplitLayout } from '../components/layout/SplitLayout'
import { ContentInputForm } from '../features/content/ContentInputForm'
import { ScenePreparing } from '../features/editor/ScenePreparing'
import { EditorWorkspace, SCENE_EDITOR_ID, type EditorTab } from '../features/editor/EditorWorkspace'
import { ProgressDock } from '../features/pipeline/ProgressDock'
import { usePipeline } from '../features/pipeline/usePipeline'
import { VideoPreview } from '../features/video/VideoPreview'
import { useToast } from '../hooks/useToast'
import { scrollToElement } from '../utils/scroll'

export function HomePage() {
  const { toasts, showToast, dismissToast, clearToasts } = useToast()
  const { state, dispatch, running, start, render, cancel, stepElapsed, stale } = usePipeline({
    onError: showToast,
    onRunStart: clearToasts,
  })
  const [tab, setTab] = useState<EditorTab>('edit')
  const [highlight, setHighlight] = useState<{ assetId: string; n: number } | null>(null)

  // 영상이 완성되면 편집 영역 위로 이동 (오른쪽, 좁은 화면에서는 위에 완성 영상이 붙는다)
  useEffect(() => {
    if (state.phase === 'done') scrollToElement(document.getElementById(SCENE_EDITOR_ID))
  }, [state.phase])

  const locate = (assetId: string) => {
    setTab('source')
    setHighlight((prev) => ({ assetId, n: (prev?.n ?? 0) + 1 }))
  }

  return (
    <PageLayout
      title="블로그 글 하나로 숏폼 한 편"
    >
      <ToastList toasts={toasts} onDismiss={dismissToast} />

      <ContentInputForm
        mode={state.mode}
        onModeChange={(mode) => dispatch({ type: 'setMode', mode })}
        onStart={(input) => {
          setHighlight(null)
          setTab('edit')
          start(input)
        }}
        running={running}
      />

      {state.content && (
        <SplitLayout asideVisible={state.result != null} aside={<VideoPreview state={state} stale={stale} />}>
          {state.scenes.length > 0 ? (
            <EditorWorkspace
              state={state}
              dispatch={dispatch}
              locked={running}
              tab={tab}
              onTabChange={setTab}
              highlight={highlight}
              onLocate={locate}
            />
          ) : (
            <ScenePreparing running={running} steps={state.steps} stepElapsed={stepElapsed} />
          )}
        </SplitLayout>
      )}

      <ProgressDock state={state} stepElapsed={stepElapsed} onRender={render} onCancel={cancel} />
    </PageLayout>
  )
}
