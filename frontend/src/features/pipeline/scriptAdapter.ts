
import type { ScriptGenerateResponse } from '../../types/api'
import { newSceneId } from './scenes'
import type { Scene } from './types'

export function toPipelineScenes(
  response: ScriptGenerateResponse,
): Scene[] {
  return [...response.scenes]
    .sort((a, b) => a.order - b.order)
    .map((scene) => ({
      id: newSceneId(),
      role: scene.role,
      narration: scene.narration,
      caption: scene.caption,
      asset_id: scene.asset_id,
      motion: 'zoom_in',
    }))
}
