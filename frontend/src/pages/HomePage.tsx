import { useEffect, useRef, useState } from 'react'
import { ToastList } from '../components/common/Toast'
import { PageLayout } from '../components/layout/PageLayout'
import { SplitLayout } from '../components/layout/SplitLayout'
import { ContentInputForm, type ContentInputHandle } from '../features/content/ContentInputForm'
import { ScenePreparing } from '../features/editor/ScenePreparing'
import { EditorWorkspace, SCENE_EDITOR_ID, type EditorTab } from '../features/editor/EditorWorkspace'
import { ProgressDock } from '../features/pipeline/ProgressDock'
import { RunProgress } from '../features/pipeline/RunProgress'
import { usePipeline } from '../features/pipeline/usePipeline'
import { VideoPreview } from '../features/video/VideoPreview'
import { useToast } from '../hooks/useToast'
import { scrollToElement } from '../utils/scroll'

export function HomePage() {
  const { toasts, showToast, dismissToast, clearToasts } = useToast()
  const { state, dispatch, running, start, render, cancel, stepElapsed, videoEta, stale } = usePipeline({
    onError: showToast,
    onRunStart: clearToasts,
  })
  const [tab, setTab] = useState<EditorTab>('edit')
  /** 장면을 자막 카드 대신 전체 보기로 보는 중인지 */
  const [bulk, setBulk] = useState(false)
  const inputRef = useRef<ContentInputHandle>(null)

  /** 아래 막대의 영상 제작: 장면이 있으면 영상만 만들고, 아직 없으면 입력한 글로 처음부터 시작 (입력이 없으면 알림) */
  const produce = () => {
    if (state.scenes.length > 0) {
      render()
      return
    }
    const issue = inputRef.current?.start()
    if (issue) showToast(issue)
  }

  // 영상이 완성되면 편집 영역 위로 이동 (오른쪽, 좁은 화면에서는 위에 완성 영상이 붙는다)
  useEffect(() => {
    if (state.phase === 'done') scrollToElement(document.getElementById(SCENE_EDITOR_ID))
  }, [state.phase])

  return (
    <PageLayout
      title="블로그 글 하나로 숏폼 한 편"
    >
      <ToastList toasts={toasts} onDismiss={dismissToast} />

      <ContentInputForm
        ref={inputRef}
        mode={state.mode}
        onModeChange={(mode) => dispatch({ type: 'setMode', mode })}
        onStart={(input) => {
          setBulk(false)
          setTab('edit')
          start(input)
        }}
        running={running}
      />

      <RunProgress state={state} stepElapsed={stepElapsed} videoEta={videoEta()} />

      {state.content && (
        <SplitLayout asideVisible={state.result != null} aside={<VideoPreview state={state} stale={stale} />}>
          {state.scenes.length > 0 ? (
            <EditorWorkspace
              state={state}
              dispatch={dispatch}
              locked={running}
              tab={tab}
              onTabChange={setTab}
              bulk={bulk}
              onBulkChange={setBulk}
            />
          ) : (
            <ScenePreparing running={running} steps={state.steps} stepElapsed={stepElapsed} />
          )}
        </SplitLayout>
      )}

      <ProgressDock state={state} stepElapsed={stepElapsed} videoEta={videoEta()} onRender={produce} onCancel={cancel} />
    </PageLayout>
  )
}
