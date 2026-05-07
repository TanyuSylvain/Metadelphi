import { useCallback } from 'react'
import { useAppStore } from '../store/appStore'
import { useChatStore } from '../store/chatStore'
import { useCoworkingStore } from '../store/coworkingStore'
import { generateUUID } from '../utils/uuid'
import type { CoworkingChatRequest } from '../types/api'

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

export function useCoworkingStream() {
  const appStore = useAppStore()
  const chatStore = useChatStore()
  const cwStore = useCoworkingStore()

  const start = useCallback(async (req: CoworkingChatRequest) => {
    const controller = new AbortController()
    appStore.beginRun(controller)
    cwStore.reset()

    chatStore.addMessage({
      id: generateUUID(),
      type: 'user',
      role: 'user',
      content: req.message,
    })

    // Add a coworking placeholder message
    const cwMsgId = generateUUID()
    useChatStore.setState((s) => ({
      messages: [...s.messages, {
        id: cwMsgId, type: 'coworking', role: 'assistant', content: '', isStreaming: true,
      }],
      streamingMessageId: cwMsgId,
    }))

    const activeToolIds: Record<string, string> = {} // tool name → store id (by round)
    let currentRound = 0

    try {
      const res = await fetch('/chat/coworking/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
        signal: controller.signal,
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const runId = res.headers.get('X-Run-ID')
      if (runId) appStore.setActiveRunId(runId)

      for await (const event of readSSE(res, controller.signal)) {
        switch (event.type) {
          case 'plan_ready':
            if (Array.isArray(event.plan)) cwStore.setPlanSteps(event.plan as string[])
            break

          case 'round_start':
            currentRound = event.round as number
            cwStore.startRound(currentRound)
            break

          case 'reasoning_chunk':
            cwStore.appendReasoning(currentRound, event.content as string)
            break

          case 'tool_start': {
            const toolId = cwStore.startTool(
              currentRound,
              event.tool_name as string,
              (event.tool_input as Record<string, unknown>) ?? {},
            )
            activeToolIds[event.tool_call_id as string] = toolId
            break
          }

          case 'tool_result': {
            const toolId = activeToolIds[event.tool_call_id as string]
            if (toolId) {
              const output = String(event.output ?? '')
              if (event.success) {
                cwStore.finishTool(currentRound, toolId, output)
              } else {
                cwStore.failTool(currentRound, toolId, output)
              }
              delete activeToolIds[event.tool_call_id as string]
            }
            break
          }

          case 'round_complete':
            cwStore.completeRound(currentRound, 'done')
            break

          case 'file_created':
            cwStore.addGeneratedFile({ path: event.file_path as string, size: event.file_size as number | undefined })
            break

          case 'file_deleted':
            cwStore.addDeletedFile(event.file_path as string)
            break

          case 'final_chunk':
            cwStore.appendFinalAnswer(event.content as string)
            break

          case 'done': {
            const finalAnswer = useCoworkingStore.getState().finalAnswer
            useChatStore.setState((s) => ({
              messages: s.messages.map((m) =>
                m.id === cwMsgId ? { ...m, content: finalAnswer, isStreaming: false } : m,
              ),
              streamingMessageId: null,
            }))
            break
          }

          case 'error':
            useChatStore.setState((s) => ({
              messages: s.messages.map((m) =>
                m.id === cwMsgId
                  ? { ...m, type: 'error', content: String(event.error), isStreaming: false }
                  : m,
              ),
              streamingMessageId: null,
            }))
            break
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        useChatStore.setState((s) => ({
          messages: s.messages.map((m) =>
            m.id === cwMsgId
              ? { ...m, type: 'error', content: (err as Error).message, isStreaming: false }
              : m,
          ),
          streamingMessageId: null,
        }))
      } else {
        useChatStore.setState((s) => ({
          messages: s.messages.map((m) =>
            m.id === cwMsgId ? { ...m, isStreaming: false } : m,
          ),
          streamingMessageId: null,
        }))
      }
    } finally {
      appStore.resetRun()
    }
  }, [appStore, chatStore, cwStore])

  return { start }
}
