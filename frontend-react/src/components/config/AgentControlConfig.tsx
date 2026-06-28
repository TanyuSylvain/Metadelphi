import { Card, InputNumber, Space, Typography } from 'antd'
import type { AgentControlConfig as AgentControlConfigType } from '../../types/models'

interface Props {
  config: AgentControlConfigType
  onChange: (config: AgentControlConfigType) => void
}

export default function AgentControlConfig({ config, onChange }: Props) {
  const update = (patch: Partial<AgentControlConfigType>) => {
    onChange({ ...config, ...patch })
  }

  return (
    <Card style={{ borderRadius: 12 }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Typography.Text style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#6b7280' }}>
            Max Tool Concurrency
          </Typography.Text>
          <InputNumber
            min={1}
            value={config.max_tool_concurrency}
            onChange={(v) => update({ max_tool_concurrency: v ?? 1 })}
            style={{ width: '100%', marginTop: 5 }}
          />
        </div>
        <div>
          <Typography.Text style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#6b7280' }}>
            Simple Max Iterations
          </Typography.Text>
          <InputNumber
            min={1}
            value={config.simple_max_tool_iterations}
            onChange={(v) => update({ simple_max_tool_iterations: v ?? 1 })}
            style={{ width: '100%', marginTop: 5 }}
          />
        </div>
        <div>
          <Typography.Text style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#6b7280' }}>
            Coworking Max Iterations
          </Typography.Text>
          <InputNumber
            min={1}
            value={config.coworking_max_tool_iterations}
            onChange={(v) => update({ coworking_max_tool_iterations: v ?? 1 })}
            style={{ width: '100%', marginTop: 5 }}
          />
        </div>
      </Space>
    </Card>
  )
}
