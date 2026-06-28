import { Button, Card, Input, Select, Space, Typography } from 'antd'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import type { McpServerConfig } from '../../types/models'

interface Props {
  servers: McpServerConfig[]
  errors: Record<string, string>
  onChange: (servers: McpServerConfig[]) => void
}

export default function McpConfig({ servers, errors, onChange }: Props) {
  const updateServer = (index: number, patch: Partial<McpServerConfig>) => {
    const next = [...servers]
    next[index] = { ...next[index], ...patch }
    onChange(next)
  }

  const addServer = () => {
    onChange([...servers, { name: '', url: '', transport: 'sse', api_key_env: '' }])
  }

  const removeServer = (index: number) => {
    onChange(servers.filter((_, i) => i !== index))
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Button type="primary" icon={<PlusOutlined />} onClick={addServer}>
        Add Server
      </Button>

      {servers.map((server, idx) => {
        const nameError = errors[`mcp.servers[${idx}].name`]
        const urlError = errors[`mcp.servers[${idx}].url`]

        return (
          <Card key={idx} style={{ borderRadius: 12, background: '#f9fafb' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 120px 1fr auto', gap: 12, alignItems: 'flex-end' }}>
              <div>
                <Typography.Text style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#6b7280' }}>
                  Name
                </Typography.Text>
                <Input
                  value={server.name}
                  placeholder="e.g. web-search"
                  onChange={(e) => updateServer(idx, { name: e.target.value })}
                  status={nameError ? 'error' : undefined}
                  style={{ marginTop: 5 }}
                />
              </div>
              <div>
                <Typography.Text style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#6b7280' }}>
                  URL
                </Typography.Text>
                <Input
                  value={server.url}
                  placeholder="https://…"
                  onChange={(e) => updateServer(idx, { url: e.target.value })}
                  status={urlError ? 'error' : undefined}
                  style={{ marginTop: 5 }}
                />
              </div>
              <div>
                <Typography.Text style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#6b7280' }}>
                  Transport
                </Typography.Text>
                <Select
                  value={server.transport}
                  onChange={(v) => updateServer(idx, { transport: v })}
                  options={[
                    { value: 'sse', label: 'sse' },
                    { value: 'stdio', label: 'stdio' },
                  ]}
                  style={{ width: '100%', marginTop: 5 }}
                />
              </div>
              <div>
                <Typography.Text style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#6b7280' }}>
                  API Key Env Var
                </Typography.Text>
                <Input
                  value={server.api_key_env || ''}
                  placeholder="ENV_VAR_NAME"
                  onChange={(e) => updateServer(idx, { api_key_env: e.target.value })}
                  style={{ marginTop: 5 }}
                />
              </div>
              <Button icon={<DeleteOutlined />} danger onClick={() => removeServer(idx)} />
            </div>

            {(nameError || urlError) && (
              <div style={{ marginTop: 8 }}>
                {nameError && (
                  <Typography.Text type="danger" style={{ fontSize: 11, display: 'block' }}>
                    {nameError}
                  </Typography.Text>
                )}
                {urlError && (
                  <Typography.Text type="danger" style={{ fontSize: 11, display: 'block' }}>
                    {urlError}
                  </Typography.Text>
                )}
              </div>
            )}
          </Card>
        )
      })}
    </Space>
  )
}
