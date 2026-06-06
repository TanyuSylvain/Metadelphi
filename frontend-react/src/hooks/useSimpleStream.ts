import { useCallback } from 'react'
import { useAppStore } from '../store/appStore'
import { useChatStore } from '../store/chatStore'
import { parseThinkBlocks, extractCitations, extractMetrics } from '../utils/thinkParser'
import type { ChatRequest } from '../types/api'
import type { StreamMetrics, Citation } from '../types/messages'
import { generateUUID } from '../utils/uuid'

const STREAM_FLUSH_MS = 250

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
  const beginRun = useAppStore((s) => s.beginRun)
  const setActiveRunId = useAppStore((s) => s.setActiveRunId)
  const resetRun = useAppStore((s) => s.resetRun)
  const addMessage = useChatStore((s) => s.addMessage)

  const start = useCallback(
    async (req: ChatRequest) => {
      const controller = new AbortController()
      beginRun(controller)

      // Add user message
      addMessage({
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
      let lastFlushedContent = ''
      let flushTimer: ReturnType<typeof window.setTimeout> | null = null

      const flushContent = () => {
        if (accContent === lastFlushedContent) return
        lastFlushedContent = accContent
        useChatStore.setState((s) => ({
          messages: s.messages.map((m) =>
            m.id === msgId ? { ...m, content: accContent } : m,
          ),
        }))
      }

      const clearFlushTimer = () => {
        if (flushTimer == null) return
        window.clearTimeout(flushTimer)
        flushTimer = null
      }

      const flushContentNow = () => {
        clearFlushTimer()
        flushContent()
      }

      const scheduleContentFlush = () => {
        if (flushTimer != null) return
        flushTimer = window.setTimeout(() => {
          flushTimer = null
          flushContent()
        }, STREAM_FLUSH_MS)
      }

      try {
        const res = await fetch('/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(req),
          signal: controller.signal,
        })

        if (!res.ok) throw new Error(`HTTP ${res.status}`)

        const runId = res.headers.get('X-Run-ID')
        if (runId) setActiveRunId(runId)

        for await (const event of readSSE(res, controller.signal)) {
          if (event.type === 'chunk') {
            accContent += event.content as string
            scheduleContentFlush()
          } else if (event.type === 'done') {
            flushContentNow()
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
            flushContentNow()
            useChatStore.setState((s) => ({
              messages: s.messages.map((m) =>
                m.id === msgId
                  ? { ...m, type: 'error', content: String(event.error), isStreaming: false }
                  : m,
              ),
              streamingMessageId: null,
            }))
          } else if (event.type === 'cancelled') {
            flushContentNow()
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
          flushContentNow()
          useChatStore.setState((s) => ({
            messages: s.messages.map((m) =>
              m.id === msgId ? { ...m, isStreaming: false } : m,
            ),
            streamingMessageId: null,
          }))
        } else {
          flushContentNow()
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
        clearFlushTimer()
        resetRun()
      }
    },
    [beginRun, setActiveRunId, resetRun, addMessage],
  )

  return { start }
}
