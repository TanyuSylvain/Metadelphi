import { Tag } from 'antd'

function scoreClass(score: number): string {
  if (score >= 90) return 'score-excellent'
  if (score >= 75) return 'score-good'
  if (score >= 60) return 'score-fair'
  return 'score-poor'
}

function scoreLabel(score: number): string {
  if (score >= 90) return 'Excellent'
  if (score >= 75) return 'Good'
  if (score >= 60) return 'Fair'
  return 'Poor'
}

interface Props {
  score: number | undefined | null
}

export default function ScoreBadge({ score }: Props) {
  if (score == null) return null
  return (
    <Tag className={scoreClass(score)} style={{ fontWeight: 600 }}>
      {score} · {scoreLabel(score)}
    </Tag>
  )
}
