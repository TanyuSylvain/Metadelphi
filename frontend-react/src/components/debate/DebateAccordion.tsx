import { useState } from 'react'
import { Card, Collapse, Space, Tag, Typography } from 'antd'
import type { DebateIteration, ModeratorInit, CriticIssue } from '../../types/debate'
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

function PassedBadge({ passed }: { passed: boolean }) {
  return passed ? (
    <Tag color="success" style={{ fontSize: 10, fontWeight: 600 }}>Passed</Tag>
  ) : (
    <Tag color="error" style={{ fontSize: 10, fontWeight: 600 }}>Needs Work</Tag>
  )
}

function IssueCard({ issue }: { issue: CriticIssue }) {
  const severityColors: Record<string, string> = {
    minor: '#d97706',
    moderate: '#ea580c',
    major: '#dc2626',
  }
  const categoryColors: Record<string, string> = {
    logic: '#7c3aed',
    facts: '#2563eb',
    completeness: '#0891b2',
    relevance: '#65a30d',
  }
  const sevColor = severityColors[issue.severity] ?? '#6b7280'
  const catColor = categoryColors[issue.category] ?? '#6b7280'

  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 6, padding: '6px 10px', marginBottom: 6 }}>
      <Space size={4} style={{ marginBottom: 4 }}>
        <Tag style={{ background: `${catColor}18`, color: catColor, border: 'none', fontSize: 10, fontWeight: 600 }}>
          {issue.category}
        </Tag>
        <Tag style={{ background: `${sevColor}18`, color: sevColor, border: 'none', fontSize: 10, fontWeight: 600 }}>
          {issue.severity}
        </Tag>
      </Space>
      <div style={{ fontSize: 12 }}>{safeStr(issue.description)}</div>
      {issue.quote && (
        <blockquote style={{ margin: '4px 0 0', paddingLeft: 8, borderLeft: '3px solid #d1d5db', color: '#6b7280', fontStyle: 'italic', fontSize: 11 }}>
          {safeStr(issue.quote)}
        </blockquote>
      )}
    </div>
  )
}

function ExpertAnswerCard({ expert }: { expert: Record<string, unknown> }) {
  const [detailsOpen, setDetailsOpen] = useState(false)
  const version = expert.version
  const confidence = expert.confidence
  const understanding = safeStr(expert.understanding)
  const corePoints = safeArr(expert.core_points)
  const details = safeStr(expert.details)
  const conclusion = safeStr(expert.conclusion)

  return (
    <Card
      size="small"
      className="agent-card-expert"
      title={
        <Space size={8}>
          <span>📝 Expert Answer</span>
          <Typography.Text type="secondary" style={{ fontSize: 11, fontWeight: 400 }}>
            v{typeof version === 'number' ? version : '?'} · {Math.round((typeof confidence === 'number' ? confidence : 0) * 100)}% confidence
          </Typography.Text>
        </Space>
      }
      styles={{ body: { fontSize: 12, color: '#374151' } }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {understanding && (
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#9ca3af', marginBottom: 3 }}>
              Understanding
            </div>
            <div>{understanding}</div>
          </div>
        )}
        {corePoints.length > 0 && (
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#9ca3af', marginBottom: 3 }}>
              Core Points
            </div>
            <ul style={{ paddingLeft: 16, margin: 0 }}>
              {corePoints.map((p, i) => <li key={i}>{p}</li>)}
            </ul>
          </div>
        )}
        {details && (
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#9ca3af', marginBottom: 3 }}>
              Details
            </div>
            <div style={{ display: detailsOpen ? 'block' : '-webkit-box', WebkitLineClamp: detailsOpen ? undefined : 3, WebkitBoxOrient: 'vertical', overflow: detailsOpen ? 'visible' : 'hidden' }}>
              {details}
            </div>
            <Typography.Link
              style={{ fontSize: 11 }}
              onClick={(e) => { e.stopPropagation(); setDetailsOpen(!detailsOpen) }}
            >
              {detailsOpen ? 'Show less' : 'Show more'}
            </Typography.Link>
          </div>
        )}
        {conclusion && (
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#9ca3af', marginBottom: 3 }}>
              Conclusion
            </div>
            <div>{conclusion}</div>
          </div>
        )}
        {!understanding && !corePoints.length && !details && !conclusion && '(no content)'}
      </div>
    </Card>
  )
}

function CriticReviewCard({ critic }: { critic: Record<string, unknown> }) {
  const score = critic.overall_score as number | undefined
  const passed = critic.passed as boolean | undefined
  const strengths = safeArr(critic.strengths)
  const suggestions = safeArr(critic.suggestions)
  const issues = critic.issues as CriticIssue[] | undefined

  return (
    <Card
      size="small"
      className="agent-card-critic"
      title={
        <Space size={8}>
          <span>🔎 Critic Review</span>
          <ScoreBadge score={score} />
          {passed != null && <PassedBadge passed={passed} />}
        </Space>
      }
      styles={{ body: { fontSize: 12, color: '#374151' } }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {Array.isArray(issues) && issues.length > 0 && (
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#9ca3af', marginBottom: 4 }}>
              Issues
            </div>
            {issues.map((issue, i) => <IssueCard key={i} issue={issue} />)}
          </div>
        )}
        {strengths.length > 0 && (
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#9ca3af', marginBottom: 3 }}>
              Strengths
            </div>
            <ul style={{ paddingLeft: 16, margin: 0 }}>
              {strengths.map((s, i) => <li key={i}>{s}</li>)}
            </ul>
          </div>
        )}
        {suggestions.length > 0 && (
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#9ca3af', marginBottom: 3 }}>
              Suggestions
            </div>
            <ul style={{ paddingLeft: 16, margin: 0 }}>
              {suggestions.map((s, i) => <li key={i}>{s}</li>)}
            </ul>
          </div>
        )}
      </div>
    </Card>
  )
}

function SynthesisCard({ synthesis }: { synthesis: Record<string, unknown> }) {
  const decision = safeStr(synthesis.decision)
  const feedback = synthesis.feedback_validation as Record<string, unknown> | undefined
  const validIssues = safeArr(feedback?.valid_issues)
  const invalidIssues = safeArr(feedback?.invalid_issues)
  const guidance = safeStr(synthesis.improvement_guidance)
  const summary = safeStr(synthesis.iteration_summary)

  return (
    <Card
      size="small"
      className="agent-card-synthesis"
      title={
        <Space size={8}>
          <span>⚖️ Moderator Synthesis</span>
          {decision === 'end' ? (
            <Tag color="success" style={{ fontSize: 10, fontWeight: 600 }}>End Debate</Tag>
          ) : (
            <Tag color="blue" style={{ fontSize: 10, fontWeight: 600 }}>Continue</Tag>
          )}
        </Space>
      }
      styles={{ body: { fontSize: 12, color: '#374151' } }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {validIssues.length > 0 && (
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#9ca3af', marginBottom: 3 }}>
              Valid Issues
            </div>
            <ul style={{ paddingLeft: 16, margin: 0 }}>
              {validIssues.map((issue, i) => <li key={i}>{issue}</li>)}
            </ul>
          </div>
        )}
        {invalidIssues.length > 0 && (
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#9ca3af', marginBottom: 3 }}>
              Invalid Criticisms
            </div>
            <ul style={{ paddingLeft: 16, margin: 0 }}>
              {invalidIssues.map((issue, i) => <li key={i}>{issue}</li>)}
            </ul>
          </div>
        )}
        {guidance && decision !== 'end' && (
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#9ca3af', marginBottom: 3 }}>
              Improvement Guidance
            </div>
            <div>{guidance}</div>
          </div>
        )}
        {summary && (
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#9ca3af', marginBottom: 3 }}>
              Summary
            </div>
            <div>{summary}</div>
          </div>
        )}
      </div>
    </Card>
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
          {iter.expert && exp && <ExpertAnswerCard expert={exp} />}
          {iter.critic && crit && <CriticReviewCard critic={crit} />}
          {iter.synthesis && syn && <SynthesisCard synthesis={syn} />}
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
