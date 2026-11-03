import { Stack } from '../../components/common/Stack'
import { Text } from '../../components/common/Text'
import type { ScriptSummary as Summary } from '../pipeline/types'
import styles from './ScriptSummary.module.css'

/** 2단계 결과: 주제와 핵심 포인트 */
export function ScriptSummary({ summary }: { summary: Summary }) {
  return (
    <Stack gap={6}>
      <Text variant="small">
        대본 주제 <strong>{summary.topic}</strong>
      </Text>
      <ul className={styles.points}>
        {summary.key_points.map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>
    </Stack>
  )
}
