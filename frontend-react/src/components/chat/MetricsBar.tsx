import { Space, Tooltip, Typography } from 'antd'
import { formatMs } from '../../utils/format'
import type { StreamMetrics } from '../../types/messages'

function getProviderInitial(modelId: string): { initial: string; color: string } {
  const lower = modelId.toLowerCase()
  if (lower.includes('mistral')) return { initial: 'M', color: '#ff6b35' }
  if (lower.includes('qwen') || lower.includes('dashscope')) return { initial: 'Q', color: '#ff6a00' }
  if (lower.includes('glm') || lower.includes('chatglm')) return { initial: 'G', color: '#1890ff' }
  if (lower.includes('minimax')) return { initial: 'MM', color: '#722ed1' }
  if (lower.includes('deepseek')) return { initial: 'DS', color: '#0e4da4' }
  if (lower.includes('gpt') || lower.includes('openai')) return { initial: 'GPT', color: '#10a37f' }
  if (lower.includes('gemini')) return { initial: 'G', color: '#4285f4' }
  return { initial: 'AI', color: '#6b7280' }
}

interface Props {
  metrics: StreamMetrics
  model?: string
}

export default function MetricsBar({ metrics, model }: Props) {
  const modelId = metrics.model_id || model || ''
  const { initial, color } = getProviderInitial(modelId)

  const tokenTitle = `${metrics.input_tokens ?? '?'} input ↑ / ${metrics.output_tokens ?? '?'} output ↓`

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        marginTop: 8,
        paddingTop: 8,
        borderTop: '1px solid #f0f0f0',
      }}
    >
      {/* Model name — left */}
      <Space size={6} align="center">
        <div
          className="provider-logo"
          style={{ background: color, fontSize: initial.length > 1 ? 8 : 10 }}
        >
          {initial}
        </div>
        <Typography.Text type="secondary" style={{ fontSize: 11 }}>
          {modelId}
        </Typography.Text>
      </Space>

      {/* Performance stats — right */}
      <Space size={6} align="center" style={{ marginLeft: 'auto' }} split={<Typography.Text type="secondary" style={{ fontSize: 11, color: '#d1d5db' }}>|</Typography.Text>}>
        {metrics.ttfb_ms != null && (
          <Typography.Text type="secondary" style={{ fontSize: 11 }}>
            TTFB {formatMs(metrics.ttfb_ms)}
          </Typography.Text>
        )}
        {metrics.total_tokens != null && (
          <Tooltip title={tokenTitle}>
            <Typography.Text type="secondary" style={{ fontSize: 11, cursor: 'default' }}>
              {metrics.total_tokens.toLocaleString()} tokens
            </Typography.Text>
          </Tooltip>
        )}
        {metrics.tps != null && (
          <Typography.Text type="secondary" style={{ fontSize: 11 }}>
            {metrics.tps.toFixed(1)} tok/s
          </Typography.Text>
        )}
      </Space>
    </div>
  )
}
