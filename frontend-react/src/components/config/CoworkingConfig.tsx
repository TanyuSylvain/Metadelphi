import { useState } from 'react'
import { Button, Input, Space, Typography } from 'antd'
import { FolderOpenOutlined } from '@ant-design/icons'
import { coworkingApi } from '../../api/coworking'

interface Props {
  workspacePath: string
  onPathChange: (path: string) => void
}

export default function CoworkingConfig({ workspacePath, onPathChange }: Props) {
  const [loading, setLoading] = useState(false)

  const handleBrowse = async () => {
    setLoading(true)
    try {
      const res = await coworkingApi.selectWorkspace()
      if (res.path) onPathChange(res.path)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        padding: '8px 16px',
        background: '#fff',
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
      }}
    >
      <Typography.Text
        style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#9ca3af', whiteSpace: 'nowrap' }}
      >
        Workspace
      </Typography.Text>
      <Space.Compact style={{ flex: 1, maxWidth: 500 }}>
        <Input
          value={workspacePath}
          readOnly
          placeholder="No workspace selected — click Browse"
          style={{ fontFamily: 'monospace', fontSize: 12, background: '#fafafa' }}
        />
        <Button
          icon={<FolderOpenOutlined />}
          onClick={handleBrowse}
          loading={loading}
        >
          Browse
        </Button>
      </Space.Compact>
    </div>
  )
}
