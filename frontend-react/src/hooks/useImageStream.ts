import { useCallback } from 'react'
import { useAppStore } from '../store/appStore'
import { useChatStore } from '../store/chatStore'
import { generateUUID } from '../utils/uuid'
import type { ChatRequest } from '../types/api'
import type { ImageData } from '../types/messages'

async function* readSSE(res: Response, signal: AbortSignal): AsyncGenerator<Record<string, unknown>> {
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
        try { yield JSON.parse(line.slice(6)) } catch { /* skip */ }
      }
    }
  } finally { reader.cancel() }
}

export function useImageStream() {
  const beginRun = useAppStore((s) => s.beginRun)
  const setActiveRunId = useAppStore((s) => s.setActiveRunId)
  const resetRun = useAppStore((s) => s.resetRun)
  const addMessage = useChatStore((s) => s.addMessage)

  const start = useCallback(async (req: ChatRequest) => {
    const controller = new AbortController()
    beginRun(controller)

    addMessage({
      id: generateUUID(),
      type: 'user',
      role: 'user',
      content: req.message,
    })

    const msgId = generateUUID()
    useChatStore.setState((s) => ({
      messages: [...s.messages, {
        id: msgId, type: 'image', role: 'assistant', content: '', isStreaming: true, images: [],
      }],
      streamingMessageId: msgId,
    }))

    let textContent = ''
    const images: ImageData[] = []

    try {
      const res = await fetch('/chat/image/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
        signal: controller.signal,
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const runId = res.headers.get('X-Run-ID')
      if (runId) setActiveRunId(runId)

      for await (const event of readSSE(res, controller.signal)) {
        if (event.type === 'text_chunk') {
          textContent += event.content as string
          useChatStore.setState((s) => ({
            messages: s.messages.map((m) =>
              m.id === msgId ? { ...m, content: textContent } : m,
            ),
          }))
        } else if (event.type === 'image') {
          images.push({
            data: event.data as string,
            mime_type: event.mime_type as string,
            index: event.index as number,
          })
          useChatStore.setState((s) => ({
            messages: s.messages.map((m) =>
              m.id === msgId ? { ...m, images: [...images] } : m,
            ),
          }))
        } else if (event.type === 'done') {
          useChatStore.setState((s) => ({
            messages: s.messages.map((m) =>
              m.id === msgId ? { ...m, isStreaming: false } : m,
            ),
            streamingMessageId: null,
          }))
        } else if (event.type === 'error') {
          useChatStore.setState((s) => ({
            messages: s.messages.map((m) =>
              m.id === msgId
                ? { ...m, type: 'error', content: String(event.message), isStreaming: false }
                : m,
            ),
            streamingMessageId: null,
          }))
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        useChatStore.setState((s) => ({
          messages: s.messages.map((m) =>
            m.id === msgId
              ? { ...m, type: 'error', content: (err as Error).message, isStreaming: false }
              : m,
          ),
          streamingMessageId: null,
        }))
      } else {
        useChatStore.setState((s) => ({
          messages: s.messages.map((m) =>
            m.id === msgId ? { ...m, isStreaming: false } : m,
          ),
          streamingMessageId: null,
        }))
      }
    } finally {
      resetRun()
    }
  }, [beginRun, setActiveRunId, resetRun, addMessage])

  return { start }
}
