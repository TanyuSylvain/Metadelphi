import { useState } from 'react'
import React from 'react'
import { Button, Input } from 'antd'
import { SendOutlined, StopOutlined } from '@ant-design/icons'

interface Props {
  onSend: (text: string) => void
  onCancel: () => void
  isProcessing: boolean
  disabled?: boolean
  placeholder?: string
}

export default function MessageInput({ onSend, onCancel, isProcessing, disabled, placeholder }: Props) {
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
        gap: 10,
        alignItems: 'flex-end',
      }}
    >
      <Input.TextArea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder || 'Type a message… (Enter to send, Shift+Enter for newline)'}
        autoSize={{ minRows: 1, maxRows: 6 }}
        disabled={disabled}
        style={{ resize: 'none', fontSize: 14 }}
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
  )
}
