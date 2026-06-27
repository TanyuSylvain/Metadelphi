import { useCallback } from 'react'
import { useAppStore } from '../store/appStore'
import { useChatStore } from '../store/chatStore'
import { useCoworkingStore } from '../store/coworkingStore'
import { generateUUID } from '../utils/uuid'
import type { CoworkingChatRequest } from '../types/api'
import type { Citation } from '../types/messages'

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
  const beginRun = useAppStore((s) => s.beginRun)
  const setActiveRunId = useAppStore((s) => s.setActiveRunId)
  const resetRun = useAppStore((s) => s.resetRun)
  const addMessage = useChatStore((s) => s.addMessage)
  const resetCoworking = useCoworkingStore((s) => s.reset)
  const setPlanSteps = useCoworkingStore((s) => s.setPlanSteps)
  const startRound = useCoworkingStore((s) => s.startRound)
  const appendReasoning = useCoworkingStore((s) => s.appendReasoning)
  const startTool = useCoworkingStore((s) => s.startTool)
  const finishTool = useCoworkingStore((s) => s.finishTool)
  const failTool = useCoworkingStore((s) => s.failTool)
  const completeRound = useCoworkingStore((s) => s.completeRound)
  const addGeneratedFile = useCoworkingStore((s) => s.addGeneratedFile)
  const addDeletedFile = useCoworkingStore((s) => s.addDeletedFile)
  const appendFinalAnswer = useCoworkingStore((s) => s.appendFinalAnswer)

  const start = useCallback(async (req: CoworkingChatRequest) => {
    const controller = new AbortController()
    beginRun(controller)
    resetCoworking()

    addMessage({
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
    let citations: Citation[] = []

    try {
      const res = await fetch('/chat/coworking/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
        signal: controller.signal,
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const runId = res.headers.get('X-Run-ID')
      if (runId) setActiveRunId(runId)

      for await (const event of readSSE(res, controller.signal)) {
        switch (event.type) {
          case 'plan_ready':
            if (Array.isArray(event.plan)) setPlanSteps(event.plan as string[])
            break

          case 'round_start':
            currentRound = event.round as number
            startRound(currentRound)
            break

          case 'reasoning_chunk':
            appendReasoning(currentRound, event.content as string)
            break

          case 'tool_start': {
            const toolId = startTool(
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
                finishTool(currentRound, toolId, output)
              } else {
                failTool(currentRound, toolId, output)
              }
              delete activeToolIds[event.tool_call_id as string]
            }
            break
          }

          case 'round_complete':
            completeRound(currentRound, 'done')
            break

          case 'file_created':
            addGeneratedFile({ path: event.file_path as string, size: event.file_size as number | undefined })
            break

          case 'file_deleted':
            addDeletedFile(event.file_path as string)
            break

          case 'citations':
            citations = (event.citations as Citation[]) ?? []
            break

          case 'final_chunk':
            appendFinalAnswer(event.content as string)
            break

          case 'done': {
            const finalAnswer = useCoworkingStore.getState().finalAnswer
            useChatStore.setState((s) => ({
              messages: s.messages.map((m) =>
                m.id === cwMsgId
                  ? { ...m, content: finalAnswer, isStreaming: false, citations: citations.length > 0 ? citations : undefined }
                  : m,
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
      resetRun()
    }
  }, [
    beginRun,
    setActiveRunId,
    resetRun,
    addMessage,
    resetCoworking,
    setPlanSteps,
    startRound,
    appendReasoning,
    startTool,
    finishTool,
    failTool,
    completeRound,
    addGeneratedFile,
    addDeletedFile,
    appendFinalAnswer,
  ])

  return { start }
}
