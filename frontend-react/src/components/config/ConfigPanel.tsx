import { useEffect, useMemo, useState } from 'react'
import { Button, Layout, Menu, message, Spin, Typography } from 'antd'
import { SaveOutlined } from '@ant-design/icons'
import type {
  AppConfig,
  ProviderConfig,
  WebSearchConfig as WebSearchConfigType,
  McpServerConfig,
  AgentControlConfig as AgentControlConfigType,
} from '../../types/models'
import { modelsApi } from '../../api/models'
import ProvidersConfig from './ProvidersConfig'
import WebSearchConfig from './WebSearchConfig'
import McpConfig from './McpConfig'
import AgentControlConfig from './AgentControlConfig'

const { Sider, Content } = Layout

type TabKey = 'providers' | 'websearch' | 'mcp' | 'agents'

const TABS: { key: TabKey; label: string; icon: string }[] = [
  { key: 'providers', label: 'Providers', icon: '🏢' },
  { key: 'websearch', label: 'WebSearch', icon: '🌐' },
  { key: 'mcp', label: 'MCP', icon: '🔌' },
  { key: 'agents', label: 'Agent Control', icon: '🤖' },
]

const PROVIDER_ORDER = ['mistral', 'qwen', 'glm', 'minimax', 'deepseek', 'openai', 'gemini']

interface ConfigPanelProps {
  onSaved?: () => void
}

export default function ConfigPanel({ onSaved }: ConfigPanelProps) {
  const [activeTab, setActiveTab] = useState<TabKey>('providers')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})

  const loadConfig = () => {
    setLoading(true)
    setLoadError(null)
    modelsApi
      .getConfig()
      .then((res) => setConfig(res.config))
      .catch((e) => {
        const msg = (e as Error).message || 'Failed to load configuration'
        setLoadError(msg)
        message.error(msg)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadConfig()
  }, [])

  const updateProviders = (providers: Record<string, ProviderConfig>) => {
    setConfig((prev) => (prev ? { ...prev, providers } : prev))
  }

  const updateWebSearch = (web_search: WebSearchConfigType) => {
    setConfig((prev) => (prev ? { ...prev, web_search } : prev))
  }

  const updateMcp = (servers: McpServerConfig[]) => {
    setConfig((prev) => (prev ? { ...prev, mcp: { servers } } : prev))
  }

  const updateAgents = (agents: AgentControlConfigType) => {
    setConfig((prev) => (prev ? { ...prev, agents } : prev))
  }

  const validate = (): boolean => {
    const errors: Record<string, string> = {}
    if (!config) return false

    // Providers
    const providers = config.providers
    const providerIds = Object.keys(providers).sort(
      (a, b) => PROVIDER_ORDER.indexOf(a) - PROVIDER_ORDER.indexOf(b)
    )

    for (const pid of providerIds) {
      const p = providers[pid]
      if (!p.models || p.models.length === 0) {
        errors[`providers.${pid}.models`] = 'At least one model is required'
      }
      const seen = new Set<string>()
      p.models?.forEach((m, idx) => {
        if (!m.id || !m.id.trim()) {
          errors[`providers.${pid}.models[${idx}].id`] = 'Model ID is required'
        } else if (seen.has(m.id)) {
          errors[`providers.${pid}.models[${idx}].id`] = `Duplicate model ID: ${m.id}`
        } else {
          seen.add(m.id)
        }
      })
    }

    // MCP
    config.mcp.servers.forEach((s, idx) => {
      if (!s.name || !s.name.trim()) {
        errors[`mcp.servers[${idx}].name`] = 'Server name is required'
      }
      if (!s.url || !s.url.trim()) {
        errors[`mcp.servers[${idx}].url`] = 'Server URL is required'
      }
    })

    setValidationErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSave = async () => {
    if (!config) return
    if (!validate()) {
      message.error('Please fix the highlighted errors before saving')
      return
    }

    setSaving(true)
    try {
      const res = await modelsApi.updateConfig(config)
      if (res.success) {
        message.success('Configuration saved')
        onSaved?.()
      } else {
        message.error(res.message)
      }
    } catch (e) {
      const data = (e as any).response?.data
      if (data?.detail?.errors) {
        setValidationErrors(
          Object.fromEntries(data.detail.errors.map((err: string) => [err.split(' ')[0], err]))
        )
        message.error('Validation failed on server')
      } else {
        message.error(data?.detail || (e as Error).message)
      }
    } finally {
      setSaving(false)
    }
  }

  const menuItems = useMemo(
    () =>
      TABS.map((tab) => ({
        key: tab.key,
        label: (
          <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>{tab.icon}</span>
            {tab.label}
          </span>
        ),
      })),
    []
  )

  if (loading || !config) {
    return (
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: '#f8f9fb', gap: 16 }}>
        {loadError ? (
          <>
            <Typography.Text type="danger">{loadError}</Typography.Text>
            <Button type="primary" onClick={loadConfig}>
              Retry
            </Button>
          </>
        ) : (
          <Spin size="large" />
        )}
      </div>
    )
  }

  return (
    <Layout style={{ flex: 1, background: '#f8f9fb', overflow: 'hidden' }}>
      <Sider
        width={200}
        style={{
          background: '#fff',
          borderRight: '1px solid #e8e8e8',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          style={{
            padding: '16px 16px 8px',
            fontSize: 11,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: 0.5,
            color: '#9ca3af',
          }}
        >
          Configuration
        </div>
        <Menu
          mode="inline"
          selectedKeys={[activeTab]}
          onClick={({ key }) => setActiveTab(key as TabKey)}
          items={menuItems}
          style={{ borderRight: 'none' }}
        />
      </Sider>

      <Content style={{ overflowY: 'auto', padding: '24px 32px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            marginBottom: 20,
          }}
        >
          <div>
            <Typography.Title level={4} style={{ margin: 0, color: '#111827' }}>
              {TABS.find((t) => t.key === activeTab)?.label}
            </Typography.Title>
            <Typography.Text type="secondary" style={{ fontSize: 13 }}>
              {activeTab === 'providers' && 'Add API keys, base URLs, and the models you want to use.'}
              {activeTab === 'websearch' && 'Configure search backends and API credentials.'}
              {activeTab === 'mcp' && 'Add or remove Model Context Protocol servers.'}
              {activeTab === 'agents' && 'Tool execution limits for the agent modes.'}
            </Typography.Text>
          </div>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            loading={saving}
            onClick={handleSave}
          >
            Save Configuration
          </Button>
        </div>

        {activeTab === 'providers' && (
          <ProvidersConfig
            providers={config.providers}
            errors={validationErrors}
            onChange={updateProviders}
          />
        )}
        {activeTab === 'websearch' && (
          <WebSearchConfig config={config.web_search} onChange={updateWebSearch} />
        )}
        {activeTab === 'mcp' && (
          <McpConfig servers={config.mcp.servers} errors={validationErrors} onChange={updateMcp} />
        )}
        {activeTab === 'agents' && (
          <AgentControlConfig config={config.agents} onChange={updateAgents} />
        )}
      </Content>
    </Layout>
  )
}
