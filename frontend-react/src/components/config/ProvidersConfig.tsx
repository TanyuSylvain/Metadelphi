import { useState } from 'react'
import {
  Button,
  Card,
  Checkbox,
  Input,
  Select,
  Space,
  Tooltip,
  Typography,
} from 'antd'
import { DeleteOutlined, ThunderboltOutlined, EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons'
import type { ProviderConfig, ModelConfig } from '../../types/models'
import { modelsApi } from '../../api/models'

const PROVIDER_OPTIONS = [
  { value: 'mistral', label: 'Mistral AI' },
  { value: 'qwen', label: 'Alibaba Qwen' },
  { value: 'glm', label: 'Zhipu GLM' },
  { value: 'minimax', label: 'MiniMax' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'openai', label: 'OpenAI / OpenAI-compatible' },
  { value: 'gemini', label: 'Google Gemini' },
]

const PROVIDER_META: Record<string, { display_name: string; console_url: string; default_base_url: string | null; has_base_url: boolean }> = {
  mistral: { display_name: 'Mistral AI', console_url: 'https://console.mistral.ai/', default_base_url: null, has_base_url: false },
  qwen: { display_name: 'Alibaba Qwen', console_url: 'https://dashscope.aliyuncs.com/', default_base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', has_base_url: true },
  glm: { display_name: 'Zhipu GLM', console_url: 'https://open.bigmodel.cn/', default_base_url: 'https://open.bigmodel.cn/api/paas/v4', has_base_url: true },
  minimax: { display_name: 'MiniMax', console_url: 'https://www.minimaxi.com/', default_base_url: 'https://api.minimaxi.com/v1', has_base_url: true },
  deepseek: { display_name: 'DeepSeek', console_url: 'https://platform.deepseek.com/', default_base_url: 'https://api.deepseek.com', has_base_url: true },
  openai: { display_name: 'OpenAI / OpenAI-compatible', console_url: 'https://platform.openai.com/api-keys', default_base_url: 'https://api.openai.com/v1', has_base_url: true },
  gemini: { display_name: 'Google Gemini', console_url: 'https://aistudio.google.com/app/apikey', default_base_url: 'https://generativelanguage.googleapis.com/v1beta/openai', has_base_url: true },
}

interface Props {
  providers: Record<string, ProviderConfig>
  errors: Record<string, string>
  onChange: (providers: Record<string, ProviderConfig>) => void
}

export default function ProvidersConfig({ providers, errors, onChange }: Props) {
  const [addValue, setAddValue] = useState<string | null>(null)
  const [testing, setTesting] = useState<Record<string, boolean>>({})
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string; latency_ms: number | null }>>({})

  const sortedIds = Object.keys(providers).sort(
    (a, b) => PROVIDER_OPTIONS.findIndex((p) => p.value === a) - PROVIDER_OPTIONS.findIndex((p) => p.value === b)
  )
  const availableToAdd = PROVIDER_OPTIONS.filter((p) => !providers[p.value])

  const updateProvider = (id: string, patch: Partial<ProviderConfig>) => {
    onChange({ ...providers, [id]: { ...providers[id], ...patch } })
  }

  const removeProvider = (id: string) => {
    const next = { ...providers }
    delete next[id]
    onChange(next)
  }

  const addProvider = () => {
    if (!addValue) return
    if (providers[addValue]) return
    const meta = PROVIDER_META[addValue]
    const newProvider: ProviderConfig = {
      api_key: null,
      base_url: meta.default_base_url,
      has_base_url: meta.has_base_url,
      display_name: meta.display_name,
      console_url: meta.console_url,
      default_base_url: meta.default_base_url,
      category: 'llm',
      models: [{ id: '', supports_thinking: false, thinking_locked: false, is_image_model: false }],
    }
    onChange({ ...providers, [addValue]: newProvider })
    setAddValue(null)
  }

  const updateModel = (providerId: string, index: number, patch: Partial<ModelConfig>) => {
    const models = [...providers[providerId].models]
    models[index] = { ...models[index], ...patch }
    updateProvider(providerId, { models })
  }

  const addModel = (providerId: string) => {
    const models = [
      ...providers[providerId].models,
      { id: '', supports_thinking: false, thinking_locked: false, is_image_model: false },
    ]
    updateProvider(providerId, { models })
  }

  const removeModel = (providerId: string, index: number) => {
    const models = providers[providerId].models.filter((_, i) => i !== index)
    updateProvider(providerId, { models })
  }

  const handleTest = async (providerId: string, modelId: string) => {
    const provider = providers[providerId]
    const model = provider.models.find((m) => m.id === modelId)
    if (!model) return

    const key = `${providerId}::${modelId}`
    setTesting((prev) => ({ ...prev, [key]: true }))
    try {
      const res = await modelsApi.testProviderModel({
        provider_id: providerId,
        model_id: modelId,
        api_key: provider.api_key || '',
        base_url: provider.base_url || undefined,
        is_image_model: model.is_image_model,
      })
      setTestResults((prev) => ({ ...prev, [key]: res }))
    } catch (e) {
      setTestResults((prev) => ({
        ...prev,
        [key]: { success: false, message: (e as Error).message, latency_ms: null },
      }))
    } finally {
      setTesting((prev) => ({ ...prev, [key]: false }))
    }
  }

  return (
    <div>
      <Space style={{ marginBottom: 18 }}>
        <Select
          placeholder="Select provider to add…"
          value={addValue}
          onChange={setAddValue}
          options={availableToAdd}
          style={{ width: 220 }}
          allowClear
        />
        <Button type="primary" onClick={addProvider} disabled={!addValue}>
          ＋ Add Provider
        </Button>
      </Space>

      {sortedIds.map((providerId) => {
        const provider = providers[providerId]
        const meta = PROVIDER_META[providerId]
        const modelsError = errors[`providers.${providerId}.models`]

        return (
          <Card
            key={providerId}
            style={{ marginBottom: 16, borderRadius: 12 }}
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: 9,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 15,
                    fontWeight: 700,
                    color: '#fff',
                    background:
                      providerId === 'openai'
                        ? '#10a37f'
                        : providerId === 'gemini'
                        ? 'linear-gradient(135deg,#4285f4,#34a853,#fbbc05,#ea4335)'
                        : providerId === 'mistral'
                        ? '#ff6b35'
                        : '#4a9eff',
                  }}
                >
                  {providerId[0].toUpperCase()}
                </div>
                <div>
                  <Typography.Text strong style={{ fontSize: 15, color: '#111827' }}>
                    {meta.display_name}
                  </Typography.Text>
                  <div style={{ fontSize: 11, color: '#6b7280' }}>
                    Get key at{' '}
                    <a href={meta.console_url} target="_blank" rel="noopener noreferrer" style={{ color: '#4a9eff' }}>
                      {meta.console_url.replace(/^https?:\/\//, '')}
                    </a>
                  </div>
                </div>
              </div>
            }
            extra={
              <Tooltip title="Remove provider">
                <Button icon={<DeleteOutlined />} danger size="small" onClick={() => removeProvider(providerId)} />
              </Tooltip>
            }
          >
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div>
                  <Typography.Text style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#6b7280' }}>
                    API Key
                  </Typography.Text>
                  <Input.Password
                    value={provider.api_key || ''}
                    placeholder="Enter API key…"
                    onChange={(e) => updateProvider(providerId, { api_key: e.target.value || null })}
                    iconRender={(visible) => (visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />)}
                    style={{ marginTop: 5 }}
                  />
                </div>
                <div>
                  <Typography.Text style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#6b7280' }}>
                    Base URL
                  </Typography.Text>
                  <Input
                    value={provider.base_url || ''}
                    placeholder={meta.default_base_url || 'Not configurable'}
                    disabled={!meta.has_base_url}
                    onChange={(e) => updateProvider(providerId, { base_url: e.target.value || null })}
                    style={{ marginTop: 5 }}
                  />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                  <Typography.Text style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', color: '#6b7280' }}>
                    Models
                  </Typography.Text>
                  <Button size="small" onClick={() => addModel(providerId)}>
                    ＋ Add Model
                  </Button>
                </div>

                {modelsError && (
                  <Typography.Text type="danger" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
                    {modelsError}
                  </Typography.Text>
                )}

                {provider.models.map((model, idx) => {
                  const key = `${providerId}::${model.id}`
                  const result = testResults[key]
                  const idError = errors[`providers.${providerId}.models[${idx}].id`]

                  return (
                    <div
                      key={idx}
                      style={{
                        padding: '10px 12px',
                        background: result && !result.success ? '#fef2f2' : result && result.success ? '#f0fdf4' : '#f9fafb',
                        border: `1px solid ${idError || (result && !result.success) ? '#fecaca' : result && result.success ? '#86efac' : '#e5e7eb'}`,
                        borderRadius: 8,
                        marginBottom: 8,
                      }}
                    >
                      <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
                        <Space wrap size="middle">
                          <Input
                            value={model.id}
                            placeholder="Model ID"
                            onChange={(e) => updateModel(providerId, idx, { id: e.target.value })}
                            style={{ flex: 1, minWidth: 180 }}
                            status={idError ? 'error' : undefined}
                          />
                          <Checkbox
                            checked={model.supports_thinking}
                            onChange={(e) => updateModel(providerId, idx, { supports_thinking: e.target.checked })}
                          >
                            Supports thinking
                          </Checkbox>
                          <Checkbox
                            checked={model.thinking_locked}
                            onChange={(e) => updateModel(providerId, idx, { thinking_locked: e.target.checked })}
                          >
                            Thinking locked
                          </Checkbox>
                          <Checkbox
                            checked={model.is_image_model}
                            onChange={(e) => updateModel(providerId, idx, { is_image_model: e.target.checked })}
                          >
                            Image model
                          </Checkbox>
                        </Space>
                        <Space>
                          <Button
                            size="small"
                            icon={<ThunderboltOutlined />}
                            loading={testing[key]}
                            onClick={() => handleTest(providerId, model.id)}
                            disabled={!model.id}
                          >
                            Test
                          </Button>
                          <Button size="small" icon={<DeleteOutlined />} danger onClick={() => removeModel(providerId, idx)} />
                        </Space>
                      </Space>

                      {idError && (
                        <Typography.Text type="danger" style={{ fontSize: 11, display: 'block', marginTop: 6 }}>
                          {idError}
                        </Typography.Text>
                      )}

                      {result && !result.success && (
                        <Typography.Text type="danger" style={{ fontSize: 11, display: 'block', marginTop: 6 }}>
                          ✗ {result.message}
                        </Typography.Text>
                      )}

                      {result && result.success && (
                        <Typography.Text type="success" style={{ fontSize: 11, display: 'block', marginTop: 6 }}>
                          ✓ {result.message}
                          {result.latency_ms !== null && result.latency_ms !== undefined
                            ? ` (${Math.round(result.latency_ms)}ms)`
                            : null}
                        </Typography.Text>
                      )}
                    </div>
                  )
                })}
              </div>
            </Space>
          </Card>
        )
      })}
    </div>
  )
}
