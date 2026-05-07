import { Card, Collapse, Space, Tag, Typography } from 'antd'
import type { DebateIteration, ModeratorInit } from '../../types/debate'
import ScoreBadge from './ScoreBadge'

interface Props {
  moderatorInit: ModeratorInit | null
  iterations: DebateIteration[]
  expandedCard: 'init' | number | null
  onCardClick: (card: 'init' | number) => void
}

function safeStr(val: unknown): string {
  if (val == null) return ''
  if (typeof val === 'string') return val
  try { return String(val) } catch { return '' }
}

function safeArr(val: unknown): string[] {
  if (Array.isArray(val)) return val.map(safeStr)
  return []
}

function ComplexityTag({ complexity }: { complexity: string }) {
  const map: Record<string, { color: string; label: string }> = {
    simple: { color: '#16a34a', label: 'Simple' },
    moderate: { color: '#d97706', label: 'Moderate' },
    complex: { color: '#dc2626', label: 'Complex' },
  }
  const entry = map[complexity] ?? { color: '#6b7280', label: complexity ?? 'Unknown' }
  return (
    <Tag style={{ background: `${entry.color}18`, color: entry.color, border: 'none', fontWeight: 600 }}>
      {entry.label}
    </Tag>
  )
}

export default function DebateAccordion({ moderatorInit, iterations, expandedCard, onCardClick }: Props) {
  const activeKeys: string[] = []
  if (expandedCard === 'init') activeKeys.push('init')
  if (typeof expandedCard === 'number') activeKeys.push(`round-${expandedCard}`)

  const items = []

  if (moderatorInit) {
    const constraints = safeArr(moderatorInit.key_constraints)
    items.push({
      key: 'init',
      label: (
        <Space size={8}>
          <span>🤔</span>
          <Typography.Text strong style={{ fontSize: 13 }}>Initial Analysis</Typography.Text>
          <ComplexityTag complexity={moderatorInit.complexity ?? 'unknown'} />
          <Tag color="blue" style={{ fontSize: 10 }}>
            {moderatorInit.decision === 'direct_answer' ? 'Direct Answer' : '→ Expert'}
          </Tag>
        </Space>
      ),
      children: (
        <div style={{ fontSize: 12, color: '#4b5563', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#9ca3af', marginBottom: 3 }}>
              Intent
            </div>
            <div>{safeStr(moderatorInit.intent)}</div>
          </div>
          {constraints.length > 0 && (
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#9ca3af', marginBottom: 3 }}>
                Key Constraints
              </div>
              <ul style={{ paddingLeft: 16, margin: 0 }}>
                {constraints.map((c, i) => <li key={i}>{c}</li>)}
              </ul>
            </div>
          )}
          {moderatorInit.complexity_reason && (
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#9ca3af', marginBottom: 3 }}>
                Complexity Reason
              </div>
              <div>{safeStr(moderatorInit.complexity_reason)}</div>
            </div>
          )}
        </div>
      ),
    })
  }

  for (const iter of iterations) {
    const score = iter.critic?.overall_score
    const exp = iter.expert as unknown as Record<string, unknown> | undefined
    const crit = iter.critic as unknown as Record<string, unknown> | undefined
    const syn = iter.synthesis as unknown as Record<string, unknown> | undefined
    const expertVer = exp?.version
    const expertConf = exp?.confidence
    const expertDetails = safeStr(exp?.details)
    const expertConclusion = safeStr(exp?.conclusion)
    const criticStrengths = safeArr(crit?.strengths)
    const criticIssues = crit?.issues

    items.push({
      key: `round-${iter.round}`,
      label: (
        <Space size={8}>
          <span>⚔️</span>
          <Typography.Text strong style={{ fontSize: 13 }}>Round {iter.round}</Typography.Text>
          <ScoreBadge score={score} />
        </Space>
      ),
      children: (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {iter.expert && (
            <Card
              size="small"
              className="agent-card-expert"
              title={
                <Space size={8}>
                  <span>📝 Expert Answer</span>
                  <Typography.Text type="secondary" style={{ fontSize: 11, fontWeight: 400 }}>
                    v{typeof expertVer === 'number' ? expertVer : '?'} · {Math.round((typeof expertConf === 'number' ? expertConf : 0) * 100)}% confidence
                  </Typography.Text>
                </Space>
              }
              styles={{ body: { fontSize: 12, color: '#374151' } }}
            >
              {expertDetails || expertConclusion || '(no content)'}
            </Card>
          )}
          {iter.critic && (
            <Card
              size="small"
              className="agent-card-critic"
              title={
                <Space size={8}>
                  <span>🔎 Critic Review</span>
                  <ScoreBadge score={crit?.overall_score as number | undefined} />
                </Space>
              }
              styles={{ body: { fontSize: 12, color: '#374151' } }}
            >
              {criticStrengths.length > 0 && (
                <div style={{ marginBottom: 6 }}>
                  <strong>Strengths:</strong> {criticStrengths.join('; ')}
                </div>
              )}
              {Array.isArray(criticIssues) && criticIssues.length > 0 && (
                <div>
                  <strong>Issues:</strong>
                  <ul style={{ paddingLeft: 16, marginTop: 4 }}>
                    {criticIssues.map((issue: unknown, i: number) => (
                      <li key={i}>{typeof issue === 'string' ? issue : safeStr((issue as Record<string, unknown>)?.description) || String(issue)}</li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          )}
          {iter.synthesis && (
            <Card
              size="small"
              className="agent-card-synthesis"
              title={
                <Space size={8}>
                  <span>⚖️ Moderator Synthesis</span>
                  <Typography.Text type="secondary" style={{ fontSize: 11, fontWeight: 400 }}>
                    {safeStr(syn?.decision)}
                  </Typography.Text>
                </Space>
              }
              styles={{ body: { fontSize: 12, color: '#374151' } }}
            >
              {safeStr(syn?.analysis)}
            </Card>
          )}
        </div>
      ),
    })
  }

  return (
    <Collapse
      accordion
      activeKey={activeKeys}
      onChange={(keys) => {
        const key = Array.isArray(keys) ? keys[0] : keys
        if (!key) return
        if (key === 'init') onCardClick('init')
        else if (key.startsWith('round-')) onCardClick(parseInt(key.replace('round-', ''), 10))
      }}
      items={items}
      style={{ background: 'transparent' }}
    />
  )
}
