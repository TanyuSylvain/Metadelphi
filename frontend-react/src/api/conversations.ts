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
  mode?: 'simple' | 'debate' | 'coworking'
  messages: Array<{
    role: string
    content: string
    timestamp: string
    model?: string
    message_type?: string
    iteration?: number
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
      const isDebateAnswer =
        m.message_type === 'final_answer' &&
        Array.isArray((m.metadata?.metrics as { model_ids?: unknown } | undefined)?.model_ids)

      // Strip embedded metadata markers from stored content
      const content = m.content
        .replace(/\n?\n?<!--METRICS_JSON[\s\S]*?METRICS_JSON-->/g, '')
        .replace(/\n?\n?<!--CITATIONS_JSON[\s\S]*?CITATIONS_JSON-->/g, '')
        .trim()

      let type: Message['type'] = 'assistant'
      let displayContent = content
      let images: Message['images'] | undefined
      if (m.role === 'user') {
        type = 'user'
      } else if (m.message_type === 'image_response') {
        try {
          const parsed = JSON.parse(content) as { text?: string; images?: Message['images'] }
          type = 'image'
          displayContent = parsed.text ?? ''
          images = Array.isArray(parsed.images) ? parsed.images : []
        } catch {
          type = 'image'
        }
      } else if (isDebateAnswer) {
        type = 'debate'
      } else if (m.message_type === 'final_answer') {
        type = 'assistant'
      }

      return {
        id: `hist-${i}`,
        type,
        role: m.role as 'user' | 'assistant',
        content: displayContent,
        timestamp: m.timestamp,
        model: m.model,
        metrics,
        images,
        debateRound: isDebateAnswer ? m.iteration : undefined,
      }
    })
}
