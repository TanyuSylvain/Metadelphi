import { useState } from 'react'
import React from 'react'
import { Button, Input, Typography } from 'antd'
import { CloseOutlined, SendOutlined, StopOutlined } from '@ant-design/icons'
import type { ImageEditSource } from '../../types/messages'

interface Props {
  onSend: (text: string) => void
  onCancel: () => void
  isProcessing: boolean
  disabled?: boolean
  placeholder?: string
  imageEditSource?: ImageEditSource | null
  onClearImageEditSource?: () => void
}

export default function MessageInput({
  onSend,
  onCancel,
  isProcessing,
  disabled,
  placeholder,
  imageEditSource,
  onClearImageEditSource,
}: Props) {
  const [value, setValue] = useState('')

  const handleSend = () => {
    const text = value.trim()
    if (!text || isProcessing) return
    setValue('')
    onSend(text)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div
      style={{
        padding: '12px 16px',
        background: '#fff',
        borderTop: '1px solid #e8e8e8',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}
    >
      {imageEditSource && (
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            width: 'fit-content',
            maxWidth: '100%',
            padding: '5px 7px',
            border: '1px solid #86efac',
            borderRadius: 6,
            background: '#dcfce7',
          }}
        >
          <img
            src={`data:${imageEditSource.mime_type};base64,${imageEditSource.data}`}
            alt=""
            style={{ width: 28, height: 28, objectFit: 'cover', borderRadius: 4 }}
          />
          <Typography.Text style={{ color: '#166534', fontSize: 12, fontWeight: 600 }}>
            Editing: {imageEditSource.label}
          </Typography.Text>
          <Button
            size="small"
            type="text"
            icon={<CloseOutlined />}
            onClick={onClearImageEditSource}
            style={{ color: '#166534' }}
          />
        </div>
      )}
      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
        <Input.TextArea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || 'Type a message… (Enter to send, Shift+Enter for newline)'}
          autoSize={{ minRows: 1, maxRows: 6 }}
          disabled={disabled}
          style={{ flex: 1, resize: 'none', fontSize: 14 }}
        />
        {isProcessing ? (
          <Button
            danger
            icon={<StopOutlined />}
            onClick={onCancel}
            style={{ flexShrink: 0 }}
          >
            Cancel
          </Button>
        ) : (
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            disabled={!value.trim() || disabled}
            style={{ flexShrink: 0 }}
          >
            Send
          </Button>
        )}
      </div>
    </div>
  )
}
