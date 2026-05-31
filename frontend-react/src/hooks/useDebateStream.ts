import { useCallback } from 'react'
import { useAppStore } from '../store/appStore'
import { useChatStore } from '../store/chatStore'
import { useDebateStore } from '../store/debateStore'
import { generateUUID } from '../utils/uuid'
import type { MultiAgentChatRequest } from '../types/api'
import type { ExpertAnswer, CriticReview, ModeratorInit, ModeratorSynthesis, DebatePhase, TerminationReason } from '../types/debate'
import type { StreamMetrics } from '../types/messages'

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

export function useDebateStream() {
  const appStore = useAppStore()
  const chatStore = useChatStore()
  const debateStore = useDebateStore()

  const start = useCallback(async (req: MultiAgentChatRequest) => {
    const controller = new AbortController()
    appStore.beginRun(controller)

    const debateId = generateUUID()
    debateStore.startDebate(debateId)

    chatStore.addMessage({
      id: generateUUID(),
      type: 'user',
      role: 'user',
      content: req.message,
    })

    try {
      const res = await fetch('/chat/multi-agent/stream', {
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
          case 'phase_start':
            debateStore.setPhase(
              event.phase as DebatePhase,
              (event.iteration as number) ?? 1,
            )
            break

          case 'moderator_init': {
            const init = event.analysis as ModeratorInit | undefined
            if (init) debateStore.setModeratorInit(init)
            break
          }

          case 'expert_answer':
            debateStore.setExpertAnswer(
              event.iteration as number,
              event.answer as ExpertAnswer,
            )
            break

          case 'critic_review':
            debateStore.setCriticReview(
              event.iteration as number,
              event.review as CriticReview,
            )
            break

          case 'moderator_synthesize': {
            const synthesis = event.analysis as ModeratorSynthesis | undefined
            if (synthesis) debateStore.setSynthesis(event.iteration as number, synthesis)
            break
          }

          case 'iteration_complete':
            debateStore.completeIteration(event.iteration as number)
            break

          case 'done': {
            const finalAnswer = event.final_answer as string
            const termination = event.termination_reason as TerminationReason
            const total = event.total_iterations as number
            const metrics = event.metrics as StreamMetrics | undefined
            if (event.was_direct_answer) debateStore.setDirectAnswer()
            debateStore.finishDebate(termination, total)

            chatStore.addMessage({
              id: generateUUID(),
              type: 'debate',
              role: 'assistant',
              content: finalAnswer,
              debateRound: total,
              debateId,
              metrics,
              model: req.models?.expert,
            })
            break
          }

          case 'error':
            chatStore.addMessage({
              id: generateUUID(),
              type: 'error',
              role: 'assistant',
              content: String(event.error),
            })
            break
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        chatStore.addMessage({
          id: generateUUID(),
          type: 'error',
          role: 'assistant',
          content: (err as Error).message,
        })
      }
    } finally {
      appStore.resetRun()
    }
  }, [appStore, chatStore, debateStore])

  return { start }
}
