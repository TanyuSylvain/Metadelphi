import { Select, Space, Switch, Tooltip, Typography } from 'antd'
import { SettingOutlined } from '@ant-design/icons'
import type { ChatMode } from '../../store/prefsStore'
import type { Model } from '../../types/models'

const ASPECT_RATIOS = ['1:1', '16:9', '4:3', '9:16', '21:9', '3:2']

interface Props {
  mode: ChatMode
  selectedModel: string
  models: Model[]
  thinkingEnabled: boolean
  markdownEnabled: boolean
  webSearchEnabled: boolean
  imageModeEnabled: boolean
  imageAspectRatio: string
  debatePanelVisible: boolean
  isProcessing: boolean
  onThinkingChange: (v: boolean) => void
  onMarkdownChange: (v: boolean) => void
  onWebSearchChange: (v: boolean) => void
  onImageModeChange: (v: boolean) => void
  onAspectRatioChange: (v: string) => void
  onDebatePanelChange: (v: boolean) => void
  onSettingsClick: () => void
}

export default function HeaderToggles({
  mode,
  selectedModel,
  models,
  thinkingEnabled,
  markdownEnabled,
  webSearchEnabled,
  imageModeEnabled,
  imageAspectRatio,
  debatePanelVisible,
  isProcessing,
  onThinkingChange,
  onMarkdownChange,
  onWebSearchChange,
  onImageModeChange,
  onAspectRatioChange,
  onDebatePanelChange,
  onSettingsClick,
}: Props) {
  const currentModel = models.find((m) => m.model_id === selectedModel)
  const supportsThinking = currentModel?.supports_thinking ?? false
  const thinkingLocked = currentModel?.thinking_locked ?? false

  const isSimple = mode === 'simple'
  const isDebate = mode === 'debate'

  const ToggleItem = ({
    label,
    checked,
    onChange,
    disabled = false,
    locked = false,
  }: {
    label: string
    checked: boolean
    onChange: (v: boolean) => void
    disabled?: boolean
    locked?: boolean
  }) => (
    <Space size={4} align="center">
      <Switch
        size="small"
        checked={checked}
        onChange={onChange}
        disabled={disabled || locked}
      />
      <Typography.Text
        style={{ fontSize: 12, color: disabled ? 'rgba(0,0,0,0.25)' : '#666', whiteSpace: 'nowrap' }}
      >
        {label}
        {locked && ' 🔒'}
      </Typography.Text>
    </Space>
  )

  return (
    <Space size={12} align="center" style={{ marginLeft: 'auto' }}>
      {/* Simple mode toggles */}
      {isSimple && !imageModeEnabled && (
        <>
          <Tooltip title={!supportsThinking ? 'This model does not support thinking mode' : undefined}>
            <span>
              <ToggleItem
                label="Thinking"
                checked={thinkingEnabled}
                onChange={onThinkingChange}
                disabled={!supportsThinking}
                locked={thinkingLocked}
              />
            </span>
          </Tooltip>
          <ToggleItem label="Web Search" checked={webSearchEnabled} onChange={onWebSearchChange} />
        </>
      )}

      {!isDebate && (
        <ToggleItem
          label="Markdown"
          checked={markdownEnabled}
          onChange={onMarkdownChange}
          disabled={imageModeEnabled}
          locked={imageModeEnabled}
        />
      )}

      {/* Image mode (simple only) */}
      {isSimple && (
        <ToggleItem
          label="Image"
          checked={imageModeEnabled}
          onChange={onImageModeChange}
          disabled={isProcessing}
        />
      )}

      {/* Aspect ratio (image mode only) */}
      {isSimple && imageModeEnabled && (
        <Space size={4} align="center">
          <Typography.Text style={{ fontSize: 12, color: '#666' }}>Ratio:</Typography.Text>
          <Select
            value={imageAspectRatio}
            onChange={onAspectRatioChange}
            options={ASPECT_RATIOS.map((r) => ({ value: r, label: r }))}
            size="small"
            style={{ width: 72 }}
          />
        </Space>
      )}

      {/* Debate panel toggle (debate mode only) */}
      {isDebate && (
        <ToggleItem
          label="Debate Panel"
          checked={debatePanelVisible}
          onChange={onDebatePanelChange}
        />
      )}

      {/* Settings button */}
      <Tooltip title="Provider Settings">
        <div
          onClick={onSettingsClick}
          style={{
            width: 32,
            height: 32,
            border: '1px solid #e8e8e8',
            borderRadius: 6,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            fontSize: 15,
            color: '#666',
            transition: 'all 0.12s',
          }}
          onMouseEnter={(e) => {
            const el = e.currentTarget as HTMLElement
            el.style.borderColor = '#4a9eff'
            el.style.color = '#4a9eff'
          }}
          onMouseLeave={(e) => {
            const el = e.currentTarget as HTMLElement
            el.style.borderColor = '#e8e8e8'
            el.style.color = '#666'
          }}
        >
          <SettingOutlined />
        </div>
      </Tooltip>
    </Space>
  )
}
