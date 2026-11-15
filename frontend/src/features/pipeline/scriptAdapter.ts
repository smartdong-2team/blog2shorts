
import type { ScriptGenerateResponse } from '../../types/api'
import { defaultMotion, newSceneId } from './scenes'
import type { Scene } from './types'

export function toPipelineScenes(
  response: ScriptGenerateResponse,
): Scene[] {
  return [...response.scenes]
    .sort((a, b) => a.order - b.order)
    .map((scene, index) => ({
      id: newSceneId(),
      role: scene.role,
      narration: scene.narration,
      caption: scene.caption,
      subtitles: scene.subtitle_pages.map((lines) => lines.join('\n')),
      asset_id: scene.asset_id,
      motion: defaultMotion(index),
    }))
}
