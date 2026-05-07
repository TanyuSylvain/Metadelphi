import { api } from './client'
import type { ConversationInfo } from '../types/models'
import type { SwitchModeRequest } from '../types/api'
import type { Message } from '../types/messages'

export interface ConversationsListResponse {
  conversations: ConversationInfo[]
  count: number
}

export interface ConversationHistoryResponse {
  conversation_id: string
  messages: Array<{
    role: string
    content: string
    timestamp: string
    model?: string
    message_type?: string
    metadata?: Record<string, unknown>
  }>
}

export const conversationsApi = {
  list: (limit = 100, offset = 0) =>
    api.get<ConversationsListResponse>(`/conversations/?limit=${limit}&offset=${offset}`),

  get: (id: string) =>
    api.get<ConversationHistoryResponse>(`/conversations/${id}`),

  getInfo: (id: string) =>
    api.get<ConversationInfo>(`/conversations/${id}/info`),

  delete: (id: string) =>
    api.delete<{ message: string }>(`/conversations/${id}`),

  deleteAll: () =>
    api.delete<{ message: string }>('/conversations/'),

  switchMode: (id: string, req: SwitchModeRequest) =>
    api.post<{ success: boolean; message: string; mode: string }>(`/conversations/${id}/switch-mode`, req),
}

export function historyToMessages(
  history: ConversationHistoryResponse,
): Message[] {
  return history.messages
    .filter((m) => m.role !== 'system')
    .map((m, i) => {
      const metrics = m.metadata?.metrics as Message['metrics'] | undefined
      // Strip embedded metadata markers from stored content
      const content = m.content
        .replace(/\n?\n?<!--METRICS_JSON[\s\S]*?METRICS_JSON-->/g, '')
        .replace(/\n?\n?<!--CITATIONS_JSON[\s\S]*?CITATIONS_JSON-->/g, '')
        .trim()

      let type: Message['type'] = 'assistant'
      if (m.role === 'user') {
        type = 'user'
      } else if (m.message_type === 'final_answer') {
        type = 'assistant'
      }

      return {
        id: `hist-${i}`,
        type,
        role: m.role as 'user' | 'assistant',
        content,
        timestamp: m.timestamp,
        model: m.model,
        metrics,
      }
    })
}
