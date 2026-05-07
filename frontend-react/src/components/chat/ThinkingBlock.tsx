import { useRef } from 'react'
import { Collapse, Typography } from 'antd'
import { BulbOutlined } from '@ant-design/icons'
import type { ThinkSegment } from '../../types/messages'

interface Props {
  segments: ThinkSegment[]
  isStreaming: boolean
}

export default function ThinkingBlock({ segments, isStreaming }: Props) {
  const openStateRef = useRef<Map<number, boolean>>(new Map())

  if (!segments || segments.length === 0) return null

  const items = segments.map((seg, i) => {
    const label = isStreaming && !seg.complete ? 'Thinking…' : `Thinking`

    return {
      key: String(i),
      label: (
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          <BulbOutlined style={{ marginRight: 6 }} />
          {label}
          {isStreaming && !seg.complete && (
            <span style={{ marginLeft: 8, fontSize: 11, color: '#9ca3af' }}>
              {seg.thinking.length} chars
            </span>
          )}
        </Typography.Text>
      ),
      children: (
        <Typography.Paragraph
          style={{
            fontFamily: 'monospace',
            fontSize: 12,
            color: '#6b7280',
            whiteSpace: 'pre-wrap',
            maxHeight: 200,
            overflow: 'auto',
            margin: 0,
          }}
        >
          {seg.thinking}
        </Typography.Paragraph>
      ),
    }
  })

  return (
    <Collapse
      size="small"
      items={items}
      defaultActiveKey={[]}
      className={isStreaming ? 'thinking-streaming' : undefined}
      style={{ marginBottom: 10, fontSize: 12 }}
      onChange={(keys) => {
        segments.forEach((_, i) => {
          openStateRef.current.set(i, keys.includes(String(i)))
        })
      }}
    />
  )
}
