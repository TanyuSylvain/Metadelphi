export type ToolStatus = 'pending' | 'running' | 'done' | 'error'

export interface ToolCall {
  id: string
  tool: string
  input: Record<string, unknown>
  result?: string
  status: ToolStatus
  durationMs?: number
}

export interface FileRecord {
  path: string
  size?: number
}

export interface CoworkingRound {
  round: number
  reasoning: string
  toolCalls: ToolCall[]
  status: 'running' | 'done' | 'error'
}
