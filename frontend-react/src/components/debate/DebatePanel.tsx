import { Typography } from 'antd'
import { useDebateStore } from '../../store/debateStore'
import { usePrefsStore } from '../../store/prefsStore'
import DebateProgress from './DebateProgress'
import DebateAccordion from './DebateAccordion'

export default function DebatePanel() {
  const debate = useDebateStore()
  const { multiAgentConfig } = usePrefsStore()

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: '#fff',
        borderLeft: '1px solid #e8e8e8',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid #f0f0f0',
          background: '#fafafa',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          flexShrink: 0,
        }}
      >
        <span style={{ fontSize: 16 }}>⚖️</span>
        <Typography.Text strong style={{ fontSize: 14 }}>
          Debate Progress
        </Typography.Text>
        <Typography.Text type="secondary" style={{ fontSize: 11, marginLeft: 'auto' }}>
          {multiAgentConfig.maxIterations} rounds max · threshold {multiAgentConfig.scoreThreshold}
        </Typography.Text>
      </div>

      {/* Progress indicator */}
      <DebateProgress
        phase={debate.currentPhase}
        currentIteration={debate.currentIteration}
        maxIterations={multiAgentConfig.maxIterations}
        termination={debate.termination}
        isDirectAnswer={debate.isDirectAnswer}
      />

      {/* Debate rounds accordion */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {debate.moderatorInit || debate.iterations.length > 0 ? (
          <DebateAccordion
            moderatorInit={debate.moderatorInit}
            iterations={debate.iterations}
            expandedCard={debate.expandedCard}
            onCardClick={debate.setExpandedCard}
          />
        ) : (
          <div
            style={{
              textAlign: 'center',
              color: '#9ca3af',
              paddingTop: 40,
              fontSize: 13,
            }}
          >
            <div style={{ fontSize: 32, marginBottom: 12 }}>⚖️</div>
            <div>Debate details will appear here</div>
            <div style={{ fontSize: 11, marginTop: 4 }}>Send a message to start the debate</div>
          </div>
        )}
      </div>
    </div>
  )
}
