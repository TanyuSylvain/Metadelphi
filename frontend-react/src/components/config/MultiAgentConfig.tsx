import { useMemo } from 'react'
import { Collapse, Select, Slider, Space, Switch, Typography } from 'antd'
import type { Model } from '../../types/models'
import type { MultiAgentConfig } from '../../store/prefsStore'

const ROLES = [
  { key: 'moderator' as const, label: '🧭 Moderator', color: '#6c63ff' },
  { key: 'expert' as const, label: '📝 Expert', color: '#4a9eff' },
  { key: 'critic' as const, label: '🔎 Critic', color: '#fb923c' },
]

interface Props {
  config: MultiAgentConfig
  models: Model[]
  onChange: (cfg: Partial<MultiAgentConfig>) => void
}

export default function MultiAgentConfigPanel({ config, models, onChange }: Props) {
  // Build grouped options (text models only)
  const modelOptions = useMemo(() => {
    const byProvider: Record<string, Model[]> = {}
    for (const m of models) {
      if (m.is_image_model) continue
      if (!byProvider[m.provider_name]) byProvider[m.provider_name] = []
      byProvider[m.provider_name].push(m)
    }
    return Object.entries(byProvider).map(([name, ms]) => ({
      label: name,
      options: ms.map((m) => ({ value: m.model_id, label: m.model_name })),
    }))
  }, [models])

  const setRoleModel = (role: keyof MultiAgentConfig, modelId: string) => {
    onChange({ [role]: modelId })
  }

  const setRoleThinking = (role: 'moderator' | 'expert' | 'critic', enabled: boolean) => {
    onChange({ thinking: { ...config.thinking, [role]: enabled } })
  }

  const currentModelSupportsThinking = (role: 'moderator' | 'expert' | 'critic') => {
    const modelId = config[role]
    const model = models.find((m) => m.model_id === modelId)
    return model?.supports_thinking ?? false
  }

  const summary = `${config.moderator || '—'} · ${config.expert || '—'} · ${config.critic || '—'}`

  return (
    <Collapse
      ghost
      size="small"
      style={{ background: '#fff', borderBottom: '1px solid #e8e8e8' }}
      items={[
        {
          key: 'config',
          label: (
            <Space size={8}>
              <span>⚙️</span>
              <Typography.Text strong style={{ fontSize: 13 }}>
                Agent Configuration
              </Typography.Text>
              <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                {summary}
              </Typography.Text>
            </Space>
          ),
          children: (
            <div style={{ padding: '4px 0 8px' }}>
              {/* Role rows */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr',
                  gap: 12,
                  marginBottom: 16,
                }}
              >
                {ROLES.map(({ key, label, color }) => (
                  <div
                    key={key}
                    style={{
                      background: '#fafafa',
                      border: '1px solid #f0f0f0',
                      borderRadius: 8,
                      padding: 12,
                    }}
                  >
                    <Typography.Text
                      strong
                      style={{ fontSize: 12, color, display: 'block', marginBottom: 8 }}
                    >
                      {label}
                    </Typography.Text>
                    <Select
                      value={config[key] || undefined}
                      onChange={(v) => setRoleModel(key, v)}
                      options={modelOptions}
                      placeholder="Select model"
                      style={{ width: '100%', marginBottom: 8 }}
                      size="small"
                      showSearch
                      filterOption={(input, opt) =>
                        String(opt?.label ?? '').toLowerCase().includes(input.toLowerCase())
                      }
                    />
                    <Space size={6} align="center">
                      <Switch
                        size="small"
                        checked={config.thinking[key]}
                        onChange={(v) => setRoleThinking(key, v)}
                        disabled={!currentModelSupportsThinking(key)}
                      />
                      <Typography.Text style={{ fontSize: 11, color: '#6b7280' }}>
                        Thinking
                      </Typography.Text>
                    </Space>
                  </div>
                ))}
              </div>

              {/* Sliders */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div
                  style={{
                    background: '#fafafa',
                    border: '1px solid #f0f0f0',
                    borderRadius: 8,
                    padding: 12,
                  }}
                >
                  <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Typography.Text strong style={{ fontSize: 12 }}>
                      🔄 Max Iterations
                    </Typography.Text>
                    <Typography.Text strong style={{ fontSize: 14, color: '#4a9eff' }}>
                      {config.maxIterations}
                    </Typography.Text>
                  </Space>
                  <Slider
                    min={1}
                    max={10}
                    value={config.maxIterations}
                    onChange={(v) => onChange({ maxIterations: v })}
                    marks={{ 1: '1', 5: '5', 10: '10' }}
                  />
                </div>
                <div
                  style={{
                    background: '#fafafa',
                    border: '1px solid #f0f0f0',
                    borderRadius: 8,
                    padding: 12,
                  }}
                >
                  <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Typography.Text strong style={{ fontSize: 12 }}>
                      🎯 Score Threshold
                    </Typography.Text>
                    <Typography.Text strong style={{ fontSize: 14, color: '#6c63ff' }}>
                      {config.scoreThreshold}
                    </Typography.Text>
                  </Space>
                  <Slider
                    min={50}
                    max={100}
                    value={config.scoreThreshold}
                    onChange={(v) => onChange({ scoreThreshold: v })}
                    marks={{ 50: '50', 75: '75', 100: '100' }}
                  />
                </div>
              </div>
            </div>
          ),
        },
      ]}
    />
  )
}
