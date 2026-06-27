import { memo } from 'react'
import { Alert, Button, Image, Space, Tag, Tooltip, Typography } from 'antd'
import { CheckOutlined, DownloadOutlined, EditOutlined } from '@ant-design/icons'
import type { ImageEditSource, Message } from '../../types/messages'
import MarkdownContent from './MarkdownContent'
import ThinkingBlock from './ThinkingBlock'
import MetricsBar from './MetricsBar'
import CopyButton from './CopyButton'

interface Props {
  message: Message
  markdownEnabled: boolean
  onDebateClick?: (debateId: string, round: number) => void
  selectedImageEditSourceId?: string | null
  onImageEditToggle?: (source: ImageEditSource) => void
}

function UserMessage({ content }: { content: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '6px 16px' }}>
      <div
        style={{
          maxWidth: '72%',
          padding: '10px 14px',
          background: '#1a1a2e',
          color: '#fff',
          borderRadius: '12px 12px 2px 12px',
          fontSize: 14,
          lineHeight: 1.65,
          wordBreak: 'break-word',
        }}
      >
        {content}
      </div>
    </div>
  )
}

function AssistantMessage({
  message,
  markdownEnabled,
}: {
  message: Message
  markdownEnabled: boolean
}) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-start', padding: '6px 16px' }}>
      <div
        style={{
          position: 'relative',
          maxWidth: '78%',
          padding: '12px 15px',
          background: '#fff',
          border: '1px solid #f0f0f0',
          borderRadius: '2px 12px 12px 12px',
          boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
          minWidth: 120,
        }}
      >
        {/* Copy button — upper-right corner, visible on hover */}
        {!message.isStreaming && (
          <div className="msg-copy-btn">
            <CopyButton content={message.content} />
          </div>
        )}

        {message.thinkSegments && message.thinkSegments.length > 0 && (
          <ThinkingBlock segments={message.thinkSegments} isStreaming={!!message.isStreaming} />
        )}

        <div className={message.isStreaming ? 'streaming-cursor' : ''}>
          <MarkdownContent content={message.content} markdownEnabled={markdownEnabled} citations={message.citations} />
        </div>

        {!message.isStreaming && message.metrics && (
          <MetricsBar metrics={message.metrics} model={message.model} />
        )}
      </div>
    </div>
  )
}

function DebateMessage({
  message,
  markdownEnabled,
  onDebateClick,
}: {
  message: Message
  markdownEnabled: boolean
  onDebateClick?: (debateId: string, round: number) => void
}) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-start', padding: '6px 16px' }}>
      <div
        style={{
          position: 'relative',
          maxWidth: '78%',
          padding: '12px 15px',
          background: '#fff',
          border: '1px solid #f0f0f0',
          borderRadius: '2px 12px 12px 12px',
          boxShadow: '0 2px 6px rgba(108,99,255,0.08)',
          cursor: onDebateClick ? 'pointer' : 'default',
          transition: 'border-color 0.15s, box-shadow 0.15s',
        }}
        onClick={() => {
          if (onDebateClick && message.debateRound != null) {
            onDebateClick(message.debateId ?? '', message.debateRound)
          }
        }}
        onMouseEnter={(e) => {
          if (!onDebateClick) return
          const el = e.currentTarget as HTMLElement
          el.style.borderColor = '#a78bfa'
          el.style.boxShadow = '0 2px 10px rgba(108,99,255,0.15)'
        }}
        onMouseLeave={(e) => {
          const el = e.currentTarget as HTMLElement
          el.style.borderColor = '#f0f0f0'
          el.style.boxShadow = '0 2px 6px rgba(108,99,255,0.08)'
        }}
      >
        {!message.isStreaming && (
          <div className="msg-copy-btn">
            <CopyButton content={message.content} />
          </div>
        )}
        <Space size={8} style={{ marginBottom: 8 }}>
          <Tag
            style={{
              background: 'linear-gradient(135deg, #6c63ff, #a78bfa)',
              color: '#fff',
              border: 'none',
              fontWeight: 600,
              fontSize: 11,
            }}
          >
            ⚖️ Debate Answer
          </Tag>
          {message.debateRound != null && (
            <Typography.Text type="secondary" style={{ fontSize: 11 }}>
              Round {message.debateRound}
            </Typography.Text>
          )}
        </Space>
        <MarkdownContent content={message.content} markdownEnabled={markdownEnabled} />
        {!message.isStreaming && message.metrics && (
          <MetricsBar metrics={message.metrics} model={message.model} />
        )}
      </div>
    </div>
  )
}

function ImageMessage({
  message,
  selectedImageEditSourceId,
  onImageEditToggle,
}: {
  message: Message
  selectedImageEditSourceId?: string | null
  onImageEditToggle?: (source: ImageEditSource) => void
}) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-start', padding: '6px 16px' }}>
      <div
        style={{
          maxWidth: '50%',
          background: '#fff',
          border: '1px solid #f0f0f0',
          borderRadius: '2px 12px 12px 12px',
          boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
          overflow: 'hidden',
        }}
      >
        {message.content && (
          <div style={{ padding: '12px 15px 8px', borderBottom: '1px solid #f3f4f6' }}>
            <Typography.Text style={{ fontSize: 13 }}>{message.content}</Typography.Text>
          </div>
        )}
        {message.images?.map((img, i) => (
          <div key={i} style={{ position: 'relative' }}>
            <Image
              src={`data:${img.mime_type};base64,${img.data}`}
              alt={`Generated image ${i + 1}`}
              style={{ maxWidth: '100%', display: 'block' }}
              preview={{ mask: 'Preview' }}
            />
            <div
              style={{
                position: 'absolute',
                bottom: 8,
                right: 8,
                display: 'flex',
                gap: 6,
              }}
            >
              <a
                href={`data:${img.mime_type};base64,${img.data}`}
                download={`image-${i + 1}.png`}
                style={{ textDecoration: 'none' }}
              >
                <Button
                  size="small"
                  icon={<DownloadOutlined />}
                  style={{
                    background: 'rgba(255,255,255,0.9)',
                    borderColor: 'rgba(209,213,219,0.9)',
                    backdropFilter: 'blur(4px)',
                  }}
                >
                  Download
                </Button>
              </a>
              {(() => {
                const sourceId = `${message.id}:${img.index ?? i}`
                const selected = selectedImageEditSourceId === sourceId
                return (
                  <Tooltip title={selected ? 'Click to stop editing this image' : 'Use this image for the next edit'}>
                    <Button
                      size="small"
                      icon={selected ? <CheckOutlined /> : <EditOutlined />}
                      onClick={() => onImageEditToggle?.({
                        ...img,
                        id: sourceId,
                        label: `Image ${img.index != null ? img.index + 1 : i + 1}`,
                      })}
                      style={{
                        background: selected ? '#dcfce7' : 'rgba(255,255,255,0.9)',
                        borderColor: selected ? '#86efac' : 'rgba(209,213,219,0.9)',
                        color: selected ? '#166534' : undefined,
                        backdropFilter: 'blur(4px)',
                      }}
                    >
                      {selected ? 'Editing' : 'Edit this'}
                    </Button>
                  </Tooltip>
                )
              })()}
            </div>
          </div>
        ))}
        {message.isStreaming && !message.images?.length && (
          <div style={{ padding: '20px', textAlign: 'center', color: '#9ca3af', fontSize: 13 }}>
            {message.imageAction === 'edit' ? 'Editing image…' : 'Generating image…'}
          </div>
        )}
      </div>
    </div>
  )
}

function CoworkingMessage({ message, markdownEnabled }: { message: Message; markdownEnabled: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-start', padding: '6px 16px' }}>
      <div
        style={{
          maxWidth: '80%',
          background: '#fff',
          border: '1px solid #e5e7eb',
          borderRadius: '2px 12px 12px 12px',
          boxShadow: '0 2px 6px rgba(0,0,0,0.06)',
          overflow: 'hidden',
        }}
      >
        {message.isStreaming ? (
          <div style={{ padding: '12px 15px', color: '#6b7280', fontSize: 13 }}>
            🛠 Agent working…
          </div>
        ) : message.content ? (
          <div style={{ padding: '12px 15px' }}>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#9ca3af', marginBottom: 8 }}>
              🛠 Agent Response
            </div>
            <MarkdownContent content={message.content} markdownEnabled={markdownEnabled} citations={message.citations} />
            <div style={{ marginTop: 8, display: 'flex', justifyContent: 'flex-end' }}>
              <CopyButton content={message.content} />
            </div>
          </div>
        ) : (
          <div style={{ padding: '12px 15px', color: '#9ca3af', fontSize: 12 }}>
            Task completed — see the worklog panel for details.
          </div>
        )}
      </div>
    </div>
  )
}

function MessageItem({
  message,
  markdownEnabled,
  onDebateClick,
  selectedImageEditSourceId,
  onImageEditToggle,
}: Props) {
  switch (message.type) {
    case 'user':
      return <UserMessage content={message.content} />

    case 'assistant':
      return <AssistantMessage message={message} markdownEnabled={markdownEnabled} />

    case 'debate':
      return <DebateMessage message={message} markdownEnabled={markdownEnabled} onDebateClick={onDebateClick} />

    case 'image':
      return (
        <ImageMessage
          message={message}
          selectedImageEditSourceId={selectedImageEditSourceId}
          onImageEditToggle={onImageEditToggle}
        />
      )

    case 'coworking':
      return <CoworkingMessage message={message} markdownEnabled={markdownEnabled} />

    case 'error':
      return (
        <div style={{ padding: '4px 16px' }}>
          <Alert
            type="error"
            message={message.content}
            showIcon
            style={{ maxWidth: '78%' }}
          />
        </div>
      )

    case 'system':
      return (
        <div style={{ padding: '4px 16px' }}>
          <Alert
            type="info"
            message={message.content}
            style={{ maxWidth: '78%', fontStyle: 'italic', fontSize: 12 }}
          />
        </div>
      )

    default:
      return null
  }
}

export default memo(MessageItem)
