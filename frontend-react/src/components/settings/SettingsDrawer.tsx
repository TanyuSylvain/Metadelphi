import { useEffect, useState } from 'react'
import { Button, Divider, Drawer, Input, message, Select, Space, Tag, Typography } from 'antd'
import { EyeInvisibleOutlined, EyeTwoTone, ThunderboltOutlined } from '@ant-design/icons'
import { modelsApi } from '../../api/models'
import type { ProviderSettings } from '../../types/models'
import type { SearchEngineStatus } from '../../types/api'

interface ProviderEntryState {
  api_key: string
  base_url: string
  testing: boolean
  testResult: { success: boolean; message: string; latency_ms: number | null } | null
}

interface Props {
  open: boolean
  onClose: () => void
}

export default function SettingsDrawer({ open, onClose }: Props) {
  const [providers, setProviders] = useState<Record<string, ProviderSettings>>({})
  const [entries, setEntries] = useState<Record<string, ProviderEntryState>>({})
  const [searchEngine, setSearchEngine] = useState<SearchEngineStatus | null>(null)
  const [selectedEngine, setSelectedEngine] = useState<'bailian' | 'tavily'>('bailian')
  const [engineSaving, setEngineSaving] = useState(false)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    Promise.all([
      modelsApi.getProviderSettings(),
      modelsApi.getSearchEngineStatus(),
    ])
      .then(([providerRes, engineRes]) => {
        setProviders(providerRes.providers)
        const e: Record<string, ProviderEntryState> = {}
        for (const [id, p] of Object.entries(providerRes.providers)) {
          e[id] = { api_key: '', base_url: p.base_url ?? '', testing: false, testResult: null }
        }
        setEntries(e)
        setSearchEngine(engineRes)
        setSelectedEngine(engineRes.default)
      })
      .finally(() => setLoading(false))
  }, [open])

  const handleTest = async (providerId: string) => {
    setEntries((prev) => ({
      ...prev,
      [providerId]: { ...prev[providerId], testing: true, testResult: null },
    }))
    try {
      const res = await modelsApi.testProvider(providerId)
      setEntries((prev) => ({
        ...prev,
        [providerId]: { ...prev[providerId], testing: false, testResult: res },
      }))
    } catch (e) {
      setEntries((prev) => ({
        ...prev,
        [providerId]: {
          ...prev[providerId],
          testing: false,
          testResult: { success: false, message: (e as Error).message, latency_ms: null },
        },
      }))
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const updates: Record<string, { api_key?: string; base_url?: string }> = {}
      for (const [id, entry] of Object.entries(entries)) {
        const update: { api_key?: string; base_url?: string } = {}
        if (entry.api_key) update.api_key = entry.api_key
        if (entry.base_url !== (providers[id]?.base_url ?? '')) update.base_url = entry.base_url
        if (Object.keys(update).length > 0) updates[id] = update
      }
      await modelsApi.updateProviderSettings(updates)

      if (searchEngine && selectedEngine !== searchEngine.default) {
        setEngineSaving(true)
        await modelsApi.updateSearchEngine({ default: selectedEngine })
        setSearchEngine((prev) => prev ? { ...prev, default: selectedEngine } : prev)
      }

      message.success('Settings saved')
      onClose()
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setSaving(false)
      setEngineSaving(false)
    }
  }

  const llmProviders = Object.entries(providers).filter(([, p]) => p.category === 'llm')
  const toolProviders = Object.entries(providers).filter(([, p]) => p.category !== 'llm')

  const renderProvider = ([id, provider]: [string, ProviderSettings]) => {
    const entry = entries[id]
    if (!entry) return null

    return (
      <div
        key={id}
        style={{
          background: '#22223a',
          border: '1px solid #2e2e4e',
          borderRadius: 10,
          overflow: 'hidden',
          marginBottom: 10,
        }}
      >
        <div style={{ padding: '12px 14px', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
          <div style={{ flex: 1 }}>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Typography.Text strong style={{ color: '#fff', fontSize: 14 }}>
                {provider.display_name}
              </Typography.Text>
              <Tag
                style={{
                  fontSize: 11,
                  background: provider.api_key_set ? '#dcfce722' : '#6b728022',
                  color: provider.api_key_set ? '#4ade80' : '#6b7280',
                  border: 'none',
                }}
              >
                {provider.api_key_set ? '✓ Configured' : 'Not configured'}
              </Tag>
            </Space>
            {provider.console_url && (
              <Typography.Text style={{ fontSize: 11, color: '#6b7280' }}>
                Get key at{' '}
                <a href={provider.console_url} target="_blank" rel="noopener noreferrer" style={{ color: '#4a9eff' }}>
                  {provider.console_url.replace(/^https?:\/\//, '')}
                </a>
              </Typography.Text>
            )}
          </div>
        </div>

        <div style={{ padding: '0 14px 12px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#6b7280', marginBottom: 4 }}>
              API Key
            </div>
            <Input.Password
              value={entry.api_key}
              onChange={(e) => setEntries((prev) => ({ ...prev, [id]: { ...prev[id], api_key: e.target.value } }))}
              placeholder={provider.api_key_set ? '••••••••••••' : 'Enter API key…'}
              style={{ background: '#1a1a2e', borderColor: '#3a3a5e', color: '#e0e0e0', fontFamily: 'monospace', fontSize: 12 }}
              iconRender={(visible) => visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />}
            />
          </div>

          {provider.has_base_url && (
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#6b7280', marginBottom: 4 }}>
                Base URL <span style={{ textTransform: 'none', fontWeight: 400, color: '#4a4a7a' }}>(optional)</span>
              </div>
              <Input
                value={entry.base_url}
                onChange={(e) => setEntries((prev) => ({ ...prev, [id]: { ...prev[id], base_url: e.target.value } }))}
                placeholder={provider.default_base_url ?? 'https://…'}
                style={{ background: '#1a1a2e', borderColor: '#3a3a5e', color: '#e0e0e0', fontSize: 12 }}
              />
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Button
              size="small"
              icon={<ThunderboltOutlined />}
              loading={entry.testing}
              onClick={() => handleTest(id)}
              style={{ borderColor: '#3a3a5e', color: '#9ca3af', background: 'transparent' }}
            >
              Test Connection
            </Button>
            {entry.testResult && (
              <Tag
                style={{
                  fontSize: 11,
                  background: entry.testResult.success ? '#dcfce722' : '#fee2e222',
                  color: entry.testResult.success ? '#4ade80' : '#f87171',
                  border: 'none',
                }}
              >
                {entry.testResult.success
                  ? `✓ Connected${entry.testResult.latency_ms ? ` · ${Math.round(entry.testResult.latency_ms)}ms` : ''}`
                  : `✗ ${entry.testResult.message}`}
              </Tag>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <Drawer
      title={
        <Space>
          <span>⚙️</span>
          <Typography.Text strong style={{ color: '#fff', fontSize: 15 }}>
            Provider Settings
          </Typography.Text>
        </Space>
      }
      placement="right"
      width={480}
      open={open}
      onClose={onClose}
      styles={{
        header: { background: '#1a1a2e', borderBottom: '1px solid #2a2a4e' },
        body: { background: '#1a1a2e', padding: '14px 16px' },
        footer: { background: '#1a1a2e', borderTop: '1px solid #2a2a4e' },
      }}
      footer={
        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
          <Button onClick={onClose} style={{ borderColor: '#3a3a5e', color: '#9ca3af', background: 'transparent' }}>
            Cancel
          </Button>
          <Button type="primary" loading={saving} onClick={handleSave}>
            💾 Save All Changes
          </Button>
        </Space>
      }
      loading={loading}
    >
      <Typography.Text style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#4a4a7a', display: 'block', marginBottom: 8 }}>
        LLM Providers
      </Typography.Text>
      {llmProviders.map(renderProvider)}

      {toolProviders.length > 0 && (
        <>
          <Divider style={{ borderColor: '#2a2a4e', margin: '14px 0 10px' }} />
          <Typography.Text style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#4a4a7a', display: 'block', marginBottom: 8 }}>
            Tool Providers
          </Typography.Text>
          {toolProviders.map(renderProvider)}
        </>
      )}

      {searchEngine && searchEngine.configured && (
        <>
          <Divider style={{ borderColor: '#2a2a4e', margin: '14px 0 10px' }} />
          <Typography.Text style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#4a4a7a', display: 'block', marginBottom: 8 }}>
            Search Engine
          </Typography.Text>
          <div
            style={{
              background: '#22223a',
              border: '1px solid #2e2e4e',
              borderRadius: 10,
              padding: '12px 14px',
            }}
          >
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#6b7280', marginBottom: 8 }}>
              Default Engine
            </div>
            <Select
              value={selectedEngine}
              onChange={(v) => setSelectedEngine(v)}
              disabled={engineSaving || !(searchEngine.available.bailian && searchEngine.available.tavily)}
              style={{ width: '100%', background: '#1a1a2e' }}
              options={[
                { value: 'bailian', label: 'Bailian (DashScope MCP)' },
                { value: 'tavily', label: 'Tavily (SDK)' },
              ]}
            />
            {!(searchEngine.available.bailian && searchEngine.available.tavily) && (
              <Typography.Text style={{ fontSize: 11, color: '#6b7280', display: 'block', marginTop: 8 }}>
                Configure both Bailian and Tavily keys to enable switching the default engine.
              </Typography.Text>
            )}
          </div>
        </>
      )}
    </Drawer>
  )
}
