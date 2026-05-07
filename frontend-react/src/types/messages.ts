export type MessageRole = 'user' | 'assistant' | 'system'
export type MessageType = 'user' | 'assistant' | 'debate' | 'image' | 'coworking' | 'system' | 'error'

export interface Citation {
  index: number
  title: string
  url: string
}

export interface StreamMetrics {
  ttfb_ms: number
  tps: number
  total_tokens: number
  input_tokens: number
  output_tokens: number
  model_id: string
}

export interface ThinkSegment {
  thinking: string
  complete: boolean
}

export interface ImageData {
  data: string
  mime_type: string
  index: number
}

export interface Message {
  id: string
  type: MessageType
  role: MessageRole
  content: string
  isStreaming?: boolean
  thinkSegments?: ThinkSegment[]
  citations?: Citation[]
  metrics?: StreamMetrics
  images?: ImageData[]
  debateRound?: number
  debateId?: string
  timestamp?: string
  model?: string
}
