import { Card, Input, Select, Space, Typography } from 'antd'
import { EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons'
import type { WebSearchConfig as WebSearchConfigType } from '../../types/models'

interface Props {
  config: WebSearchConfigType
  onChange: (config: WebSearchConfigType) => void
}

export default function WebSearchConfig({ config, onChange }: Props) {
  const update = (patch: Partial<WebSearchConfigType>) => {
    onChange({ ...config, ...patch })
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Card style={{ borderRadius: 12 }}>
        <Typography.Text style={{ fontSize: 14, fontWeight: 600, color: '#111827', display: 'block', marginBottom: 14 }}>
          Default Search Engine
        </Typography.Text>
        <Select
          value={config.default_engine}
          onChange={(v) => update({ default_engine: v })}
          options={[
            { value: 'bailian', label: 'Bailian (DashScope MCP)' },
            { value: 'tavily', label: 'Tavily (SDK)' },
          ]}
          style={{ width: 320 }}
        />
      </Card>

      <Card style={{ borderRadius: 12 }}>
        <Typography.Text style={{ fontSize: 14, fontWeight: 600, color: '#111827', display: 'block', marginBottom: 14 }}>
          API Keys
        </Typography.Text>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Typography.Text style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#6b7280' }}>
              Bailian / DashScope API Key
            </Typography.Text>
            <Input.Password
              value={config.bailian_api_key || ''}
              placeholder="Enter API key…"
              onChange={(e) => update({ bailian_api_key: e.target.value || null })}
              iconRender={(visible) => (visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />)}
              style={{ marginTop: 5 }}
            />
          </div>
          <div>
            <Typography.Text style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#6b7280' }}>
              Tavily API Key
            </Typography.Text>
            <Input.Password
              value={config.tavily_api_key || ''}
              placeholder="Enter API key…"
              onChange={(e) => update({ tavily_api_key: e.target.value || null })}
              iconRender={(visible) => (visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />)}
              style={{ marginTop: 5 }}
            />
          </div>
        </Space>
      </Card>
    </Space>
  )
}
