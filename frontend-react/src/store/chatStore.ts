import { create } from 'zustand'
import { generateUUID } from '../utils/uuid'
import type { Message, ThinkSegment, Citation, StreamMetrics, ImageData, ImageEditSource } from '../types/messages'

interface ChatState {
  conversationId: string
  messages: Message[]
  streamingMessageId: string | null
  imageEditSource: ImageEditSource | null

  setConversationId: (id: string) => void
  setMessages: (msgs: Message[]) => void
  setImageEditSource: (source: ImageEditSource | null) => void
  clearImageEditSource: () => void
  addMessage: (msg: Message) => void
  addStreamingPlaceholder: (type?: Message['type']) => string
  appendChunk: (id: string, content: string) => void
  setThinkSegments: (id: string, segments: ThinkSegment[]) => void
  finalizeMessage: (
    id: string,
    opts?: {
      citations?: Citation[]
      metrics?: StreamMetrics
      images?: ImageData[]
      debateRound?: number
      debateId?: string
    },
  ) => void
  setStreamError: (id: string, error: string) => void
  markCancelled: (id: string) => void
  removeStreamingIndicator: () => void
  clearMessages: () => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversationId: generateUUID(),
  messages: [],
  streamingMessageId: null,
  imageEditSource: null,

  setConversationId: (id) => set({ conversationId: id, imageEditSource: null }),
  setMessages: (msgs) => set({ messages: msgs }),
  setImageEditSource: (source) => set({ imageEditSource: source }),
  clearImageEditSource: () => set({ imageEditSource: null }),

  addMessage: (msg) =>
    set((s) => ({ messages: [...s.messages, msg] })),

  addStreamingPlaceholder: (type = 'assistant') => {
    const id = generateUUID()
    set((s) => ({
      messages: [
        ...s.messages,
        { id, type, role: 'assistant', content: '', isStreaming: true },
      ],
      streamingMessageId: id,
    }))
    return id
  },

  appendChunk: (id, content) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + content } : m,
      ),
    })),

  setThinkSegments: (id, segments) =>
    set((s) => ({
      messages: s.messages.map((m) => (m.id === id ? { ...m, thinkSegments: segments } : m)),
    })),

  finalizeMessage: (id, opts = {}) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id
          ? {
              ...m,
              isStreaming: false,
              ...opts,
            }
          : m,
      ),
      streamingMessageId: null,
    })),

  setStreamError: (id, error) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, type: 'error', content: error, isStreaming: false } : m,
      ),
      streamingMessageId: null,
    })),

  markCancelled: (id) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, isStreaming: false } : m,
      ),
      streamingMessageId: null,
    })),

  removeStreamingIndicator: () => {
    const { streamingMessageId } = get()
    if (!streamingMessageId) return
    set((s) => ({
      messages: s.messages.filter((m) => m.id !== streamingMessageId),
      streamingMessageId: null,
    }))
  },

  clearMessages: () => set({ messages: [], streamingMessageId: null, imageEditSource: null }),
}))
