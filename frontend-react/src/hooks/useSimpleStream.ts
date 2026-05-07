import { useCallback } from 'react'
import { useAppStore } from '../store/appStore'
import { useChatStore } from '../store/chatStore'
import { parseThinkBlocks, extractCitations, extractMetrics } from '../utils/thinkParser'
import type { ChatRequest } from '../types/api'
import type { StreamMetrics, Citation } from '../types/messages'
import { generateUUID } from '../utils/uuid'

async function* readSSE(
  res: Response,
  signal: AbortSignal,
): AsyncGenerator<Record<string, unknown>> {
  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    while (!signal.aborted) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          yield JSON.parse(line.slice(6)) as Record<string, unknown>
        } catch { /* skip malformed */ }
      }
    }
  } finally {
    reader.cancel()
  }
}

export function useSimpleStream() {
  const appStore = useAppStore()
  const chatStore = useChatStore()

  const start = useCallback(
    async (req: ChatRequest) => {
      const controller = new AbortController()
      appStore.beginRun(controller)

      // Add user message
      chatStore.addMessage({
        id: generateUUID(),
        type: 'user',
        role: 'user',
        content: req.message,
      })

      // Add streaming placeholder
      const msgId = generateUUID()
      useChatStore.setState((s) => ({
        messages: [...s.messages, { id: msgId, type: 'assistant', role: 'assistant', content: '', isStreaming: true }],
        streamingMessageId: msgId,
      }))

      let accContent = ''

      try {
        const res = await fetch('/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(req),
          signal: controller.signal,
        })

        if (!res.ok) throw new Error(`HTTP ${res.status}`)

        const runId = res.headers.get('X-Run-ID')
        if (runId) appStore.setActiveRunId(runId)

        for await (const event of readSSE(res, controller.signal)) {
          if (event.type === 'chunk') {
            accContent += event.content as string
            useChatStore.setState((s) => ({
              messages: s.messages.map((m) =>
                m.id === msgId ? { ...m, content: accContent } : m,
              ),
            }))
          } else if (event.type === 'done') {
            // Extract metadata
            const { citations, clean: c1 } = extractCitations(accContent)
            const { metrics, clean: c2 } = extractMetrics(c1)
            const { segments } = parseThinkBlocks(c2)

            useChatStore.setState((s) => ({
              messages: s.messages.map((m) =>
                m.id === msgId
                  ? {
                      ...m,
                      content: c2,
                      isStreaming: false,
                      thinkSegments: segments.length > 0 ? segments : undefined,
                      citations: (citations as Citation[]).length > 0 ? citations as Citation[] : undefined,
                      metrics: metrics as StreamMetrics | undefined,
                    }
                  : m,
              ),
              streamingMessageId: null,
            }))
          } else if (event.type === 'error') {
            useChatStore.setState((s) => ({
              messages: s.messages.map((m) =>
                m.id === msgId
                  ? { ...m, type: 'error', content: String(event.error), isStreaming: false }
                  : m,
              ),
              streamingMessageId: null,
            }))
          } else if (event.type === 'cancelled') {
            useChatStore.setState((s) => ({
              messages: s.messages.map((m) =>
                m.id === msgId ? { ...m, isStreaming: false } : m,
              ),
              streamingMessageId: null,
            }))
          }
        }
      } catch (err) {
        if ((err as Error).name === 'AbortError') {
          useChatStore.setState((s) => ({
            messages: s.messages.map((m) =>
              m.id === msgId ? { ...m, isStreaming: false } : m,
            ),
            streamingMessageId: null,
          }))
        } else {
          useChatStore.setState((s) => ({
            messages: s.messages.map((m) =>
              m.id === msgId
                ? { ...m, type: 'error', content: (err as Error).message, isStreaming: false }
                : m,
            ),
            streamingMessageId: null,
          }))
        }
      } finally {
        appStore.resetRun()
      }
    },
    [appStore, chatStore],
  )

  return { start }
}
