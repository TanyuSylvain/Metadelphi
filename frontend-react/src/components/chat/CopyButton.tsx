import React, { useState } from 'react'
import { Button, message, Tooltip } from 'antd'
import { CopyOutlined, CheckOutlined } from '@ant-design/icons'
import { copyToClipboard } from '../../utils/clipboard'
import { stripThinkBlocks, extractCitations, extractMetrics } from '../../utils/thinkParser'

interface Props {
  content: string
  style?: React.CSSProperties
}

export default function CopyButton({ content, style }: Props) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    // Strip thinking, citations, metrics metadata
    let clean = stripThinkBlocks(content)
    const { clean: c1 } = extractCitations(clean)
    const { clean: c2 } = extractMetrics(c1)
    clean = c2

    const ok = await copyToClipboard(clean)
    if (ok) {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } else {
      message.error('Failed to copy')
    }
  }

  return (
    <Tooltip title={copied ? 'Copied!' : 'Copy (clean)'}>
      <Button
        size="small"
        icon={copied ? <CheckOutlined style={{ color: '#22c55e' }} /> : <CopyOutlined />}
        onClick={handleCopy}
        style={{ fontSize: 11, ...style }}
      >
        {copied ? 'Copied' : 'Copy'}
      </Button>
    </Tooltip>
  )
}
