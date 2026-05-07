import { Collapse, List, Space, Spin, Timeline, Typography } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, FileOutlined } from '@ant-design/icons'
import { useCoworkingStore } from '../../store/coworkingStore'
import { formatFileSize } from '../../utils/format'

function ToolCallCard({
  toolCall,
}: {
  toolCall: import('../../types/coworking').ToolCall
}) {
  const statusIcon =
    toolCall.status === 'running' ? (
      <Spin size="small" />
    ) : toolCall.status === 'done' ? (
      <CheckCircleOutlined style={{ color: '#22c55e' }} />
    ) : (
      <CloseCircleOutlined style={{ color: '#ef4444' }} />
    )

  return (
    <Collapse
      size="small"
      style={{ marginBottom: 4, background: '#fafafa', borderRadius: 6 }}
      items={[
        {
          key: 'tool',
          label: (
            <Space size={8} align="center">
              {statusIcon}
              <Typography.Text strong style={{ fontSize: 12 }}>
                {toolCall.tool}
              </Typography.Text>
              <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                {Object.values(toolCall.input)[0] != null
                  ? String(Object.values(toolCall.input)[0]).slice(0, 40)
                  : ''}
              </Typography.Text>
            </Space>
          ),
          children: (
            <div style={{ fontSize: 11, color: '#374151' }}>
              <div style={{ marginBottom: 6 }}>
                <div
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.4px',
                    color: '#9ca3af',
                    marginBottom: 3,
                  }}
                >
                  Input
                </div>
                <pre
                  style={{
                    background: '#f6f8fa',
                    border: '1px solid #e5e7eb',
                    borderRadius: 4,
                    padding: '6px 8px',
                    fontSize: 11,
                    overflow: 'auto',
                    margin: 0,
                  }}
                >
                  {JSON.stringify(toolCall.input, null, 2)}
                </pre>
              </div>
              {toolCall.result && (
                <div>
                  <div
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '0.4px',
                      color: '#9ca3af',
                      marginBottom: 3,
                    }}
                  >
                    Output
                  </div>
                  <pre
                    style={{
                      background: '#f6f8fa',
                      border: '1px solid #e5e7eb',
                      borderRadius: 4,
                      padding: '6px 8px',
                      fontSize: 11,
                      overflow: 'auto',
                      margin: 0,
                      color: toolCall.status === 'error' ? '#dc2626' : 'inherit',
                    }}
                  >
                    {toolCall.result}
                  </pre>
                </div>
              )}
            </div>
          ),
        },
      ]}
    />
  )
}

export default function CoworkingPanel() {
  const { planSteps, rounds, generatedFiles, deletedFiles } = useCoworkingStore()

  const totalTools = rounds.reduce((sum, r) => sum + r.toolCalls.length, 0)

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
        <span style={{ fontSize: 16 }}>🛠</span>
        <Typography.Text strong style={{ fontSize: 14 }}>
          Agent Worklog
        </Typography.Text>
        {rounds.length > 0 && (
          <Typography.Text type="secondary" style={{ fontSize: 11, marginLeft: 'auto' }}>
            Round {rounds.length} · {totalTools} tools
          </Typography.Text>
        )}
      </div>

      <div style={{ flex: 1, overflow: 'auto' }}>
        {rounds.length === 0 && planSteps.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#9ca3af', paddingTop: 40, fontSize: 13 }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>🛠</div>
            <div>Agent work will appear here</div>
          </div>
        ) : (
          <>
            {/* Plan */}
            {planSteps.length > 0 && (
              <div style={{ padding: '12px 14px', borderBottom: '1px solid #f3f4f6' }}>
                <div
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    color: '#9ca3af',
                    marginBottom: 8,
                  }}
                >
                  📋 Plan
                </div>
                <ol style={{ paddingLeft: 18, margin: 0, fontSize: 12, color: '#374151', lineHeight: 1.7 }}>
                  {planSteps.map((step, i) => (
                    <li key={i}>{step}</li>
                  ))}
                </ol>
              </div>
            )}

            {/* Timeline */}
            {rounds.length > 0 && (
              <div style={{ padding: '12px 14px', borderBottom: '1px solid #f3f4f6' }}>
                <div
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    color: '#9ca3af',
                    marginBottom: 10,
                  }}
                >
                  ⚙️ Tool Executions
                </div>
                <Timeline
                  items={rounds.map((round) => ({
                    color:
                      round.status === 'running'
                        ? 'blue'
                        : round.status === 'done'
                        ? 'green'
                        : 'red',
                    children: (
                      <div>
                        <div
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            textTransform: 'uppercase',
                            letterSpacing: '0.4px',
                            color: '#9ca3af',
                            marginBottom: 4,
                          }}
                        >
                          Round {round.round}
                          {round.status === 'running' && (
                            <Spin size="small" style={{ marginLeft: 6 }} />
                          )}
                        </div>
                        {round.reasoning && (
                          <Typography.Paragraph
                            style={{ fontSize: 12, color: '#4b5563', marginBottom: 8 }}
                            ellipsis={{ rows: 3, expandable: true, symbol: 'more' }}
                          >
                            {round.reasoning}
                          </Typography.Paragraph>
                        )}
                        {round.toolCalls.map((tc) => (
                          <ToolCallCard key={tc.id} toolCall={tc} />
                        ))}
                      </div>
                    ),
                  }))}
                />
              </div>
            )}

            {/* Generated files */}
            {generatedFiles.length > 0 && (
              <div style={{ padding: '12px 14px' }}>
                <div
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    color: '#9ca3af',
                    marginBottom: 8,
                  }}
                >
                  📁 Generated Files ({generatedFiles.length})
                </div>
                <List
                  size="small"
                  dataSource={generatedFiles}
                  renderItem={(file) => (
                    <List.Item style={{ padding: '4px 0', border: 'none' }}>
                      <Space size={6}>
                        <FileOutlined style={{ color: '#4a9eff', fontSize: 12 }} />
                        <Typography.Text
                          style={{
                            fontSize: 11,
                            fontFamily: 'monospace',
                            color: deletedFiles.includes(file.path) ? '#9ca3af' : '#374151',
                            textDecoration: deletedFiles.includes(file.path) ? 'line-through' : undefined,
                          }}
                        >
                          {file.path}
                        </Typography.Text>
                        {file.size != null && (
                          <Typography.Text type="secondary" style={{ fontSize: 10 }}>
                            {formatFileSize(file.size)}
                          </Typography.Text>
                        )}
                      </Space>
                    </List.Item>
                  )}
                />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
