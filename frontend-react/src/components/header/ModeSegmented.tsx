import { Segmented } from 'antd'
import type { ChatMode } from '../../store/prefsStore'

const OPTIONS = [
  { value: 'simple', label: '💬 Simple' },
  { value: 'debate', label: '⚖️ Debate' },
  { value: 'coworking', label: '🛠 Coworking' },
]

interface Props {
  value: ChatMode
  onChange: (mode: ChatMode) => void
  disabled?: boolean
}

export default function ModeSegmented({ value, onChange, disabled }: Props) {
  return (
    <Segmented
      options={OPTIONS}
      value={value}
      onChange={(v) => onChange(v as ChatMode)}
      disabled={disabled}
      style={{ flexShrink: 0 }}
    />
  )
}
