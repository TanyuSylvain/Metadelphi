import { Button, Empty, Popconfirm, Spin, Typography } from 'antd'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import { formatRelativeTime } from '../../utils/format'
import type { ConversationInfo } from '../../types/models'

const MODE_COLORS: Record<string, string> = {
  simple: '#4a9eff',
  debate: '#a78bfa',
  coworking: '#34d399',
}

const MODE_LABELS: Record<string, string> = {
  simple: 'Simple',
  debate: 'Debate',
  coworking: 'Coworking',
}

function getConversationModes(conv: ConversationInfo): string[] {
  const history = conv.metadata?.mode_history
  if (Array.isArray(history) && history.length > 0) {
    return history.filter((mode): mode is string => typeof mode === 'string')
  }
  return []
}

interface Props {
  conversations: ConversationInfo[]
  loading: boolean
  currentId: string
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
  onDeleteAll: () => void
}

export default function ConversationList({
  conversations,
  loading,
  currentId,
  onSelect,
  onNew,
  onDelete,
  onDeleteAll,
}: Props) {
  const resolveModes = (conv: ConversationInfo) => {
    const usedModes = getConversationModes(conv)
    if (usedModes.length > 0) return usedModes
    return conv.id === currentId ? [] : (conv.mode ? [conv.mode] : [])
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Logo */}
      <div
        style={{
          padding: '14px 14px 12px',
          borderBottom: '1px solid #2a2a4e',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: 'linear-gradient(135deg, #4a9eff, #6c63ff)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 16,
            flexShrink: 0,
          }}
        >
          🧠
        </div>
        <Typography.Text strong style={{ color: '#fff', fontSize: 15 }}>
          Metadelphi
        </Typography.Text>
      </div>

      {/* New conversation button */}
      <div style={{ padding: '10px 12px' }}>
        <Button
          icon={<PlusOutlined />}
          onClick={onNew}
          block
          type="primary"
          style={{ background: '#4a9eff', borderColor: '#4a9eff' }}
        >
          New Conversation
        </Button>
      </div>

      {/* Conversation list */}
      <div style={{ flex: 1, overflow: 'auto', padding: '4px 8px' }}>
        {loading ? (
          <div style={{ textAlign: 'center', paddingTop: 32 }}>
            <Spin size="small" />
          </div>
        ) : conversations.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <span style={{ color: '#4a4a7a', fontSize: 12 }}>No conversations yet</span>
            }
            style={{ marginTop: 32 }}
          />
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => onSelect(conv.id)}
              style={{
                padding: '8px 10px',
                borderRadius: 6,
                marginBottom: 2,
                cursor: 'pointer',
                background: conv.id === currentId ? '#3a3a5e' : 'transparent',
                borderLeft: conv.id === currentId ? '3px solid #4a9eff' : '3px solid transparent',
                transition: 'background 0.12s',
                position: 'relative',
                display: 'flex',
                flexDirection: 'column',
                gap: 3,
              }}
              onMouseEnter={(e) => {
                const del = e.currentTarget.querySelector('.conv-del') as HTMLElement
                if (del) del.style.opacity = '1'
              }}
              onMouseLeave={(e) => {
                const del = e.currentTarget.querySelector('.conv-del') as HTMLElement
                if (del) del.style.opacity = '0'
              }}
            >
              <div
                style={{
                  fontSize: 12,
                  color: conv.id === currentId ? '#fff' : 'rgba(255,255,255,0.7)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  paddingRight: 20,
                  fontWeight: conv.id === currentId ? 500 : 400,
                }}
              >
                {conv.title || 'New Conversation'}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                {resolveModes(conv).map((mode) => (
                  <span
                    key={`${conv.id}-${mode}`}
                    style={{
                      fontSize: 10,
                      padding: '1px 5px',
                      borderRadius: 3,
                      background: `${MODE_COLORS[mode] ?? '#4a9eff'}22`,
                      color: MODE_COLORS[mode] ?? '#4a9eff',
                      fontWeight: 600,
                    }}
                  >
                    {MODE_LABELS[mode] ?? mode}
                  </span>
                ))}
                <span style={{ fontSize: 10, color: '#5a5a7a' }}>
                  {formatRelativeTime(conv.updated_at)}
                </span>
              </div>

              <Popconfirm
                title="Delete this conversation?"
                onConfirm={(e) => {
                  e?.stopPropagation()
                  onDelete(conv.id)
                }}
                okText="Delete"
                okButtonProps={{ danger: true }}
                cancelText="Cancel"
              >
                <button
                  className="conv-del"
                  onClick={(e) => e.stopPropagation()}
                  style={{
                    position: 'absolute',
                    right: 6,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    opacity: 0,
                    background: 'none',
                    border: 'none',
                    color: '#6a6a8a',
                    cursor: 'pointer',
                    fontSize: 13,
                    padding: '4px',
                    borderRadius: 4,
                    transition: 'opacity 0.15s, color 0.12s',
                  }}
                >
                  <DeleteOutlined />
                </button>
              </Popconfirm>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      {conversations.length > 0 && (
        <div style={{ padding: '10px 12px', borderTop: '1px solid #2a2a4e' }}>
          <Popconfirm
            title="Delete all conversations? This cannot be undone."
            onConfirm={onDeleteAll}
            okText="Delete All"
            okButtonProps={{ danger: true }}
            cancelText="Cancel"
          >
            <Button
              icon={<DeleteOutlined />}
              danger
              ghost
              block
              size="small"
              style={{ borderColor: '#3a3a5e', color: '#6a6a8a' }}
            >
              Delete All
            </Button>
          </Popconfirm>
        </div>
      )}
    </div>
  )
}
