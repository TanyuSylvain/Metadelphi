import { Typography } from 'antd'
import type { DebatePhase, TerminationReason } from '../../types/debate'

const PHASE_INFO: Record<
  string,
  { icon: string; label: string; desc: string }
> = {
  moderator_init: { icon: '🔍', label: 'Analyzing', desc: 'Moderator analyzing question complexity' },
  expert_generate: { icon: '📝', label: 'Expert', desc: 'Expert generating answer' },
  critic_review: { icon: '🔎', label: 'Critic', desc: 'Critic reviewing answer' },
  moderator_synthesize: { icon: '⚖️', label: 'Synthesizing', desc: 'Moderator synthesizing results' },
}

const TERMINATION_LABELS: Record<string, string> = {
  score_threshold: 'Score threshold reached',
  explicit_pass: 'Critic approved',
  max_iterations: 'Max iterations reached',
  convergence: 'Answer converged',
  simple_question: 'Direct answer provided',
}

interface Props {
  phase: DebatePhase
  currentIteration: number
  maxIterations: number
  termination: TerminationReason
  isDirectAnswer: boolean
}

export default function DebateProgress({ phase, currentIteration, maxIterations, termination, isDirectAnswer }: Props) {
  if (!phase && !termination) return null

  const info = phase ? PHASE_INFO[phase] : null
  const isDone = !!termination

  return (
    <div
      style={{
        padding: '12px 16px',
        background: '#f8f8ff',
        borderBottom: '1px solid #eeecff',
      }}
    >
      {/* Phase indicator */}
      {!isDone && info && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              background: '#eef2ff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 16,
              animation: 'spin-slow 2s linear infinite',
            }}
          >
            {info.icon}
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#4338ca' }}>{info.label}</div>
            <div style={{ fontSize: 11, color: '#6b7280', marginTop: 1 }}>{info.desc}</div>
          </div>
        </div>
      )}

      {isDone && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
          <span style={{ fontSize: 18 }}>✅</span>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#16a34a' }}>Debate Complete</div>
            <div style={{ fontSize: 11, color: '#6b7280' }}>
              {TERMINATION_LABELS[termination ?? ''] ?? termination}
            </div>
          </div>
        </div>
      )}

      {/* Iteration dots */}
      {!isDirectAnswer && (
        <>
          <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
            Round {isDone ? currentIteration - 1 : currentIteration} of {maxIterations}
          </Typography.Text>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            {Array.from({ length: maxIterations }).map((_, i) => {
              const round = i + 1
              const isDoneRound = isDone ? round <= currentIteration - 1 : round < currentIteration
              const isCurrentRound = !isDone && round === currentIteration
              return (
                <div
                  key={i}
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    background: isDoneRound
                      ? '#22c55e'
                      : isCurrentRound
                      ? '#4a9eff'
                      : '#d1d5db',
                    boxShadow: isCurrentRound ? '0 0 0 3px rgba(74,158,255,0.2)' : undefined,
                    transition: 'all 0.2s',
                  }}
                />
              )
            })}
          </div>
        </>
      )}

      {isDirectAnswer && (
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          Simple question → Direct answer
        </Typography.Text>
      )}

      <style>{`
        @keyframes spin-slow { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  )
}
