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
  const beginRun = useAppStore((s) => s.beginRun)
  const setActiveRunId = useAppStore((s) => s.setActiveRunId)
  const resetRun = useAppStore((s) => s.resetRun)
  const addMessage = useChatStore((s) => s.addMessage)
  const startDebate = useDebateStore((s) => s.startDebate)
  const setPhase = useDebateStore((s) => s.setPhase)
  const setModeratorInit = useDebateStore((s) => s.setModeratorInit)
  const setExpertAnswer = useDebateStore((s) => s.setExpertAnswer)
  const setCriticReview = useDebateStore((s) => s.setCriticReview)
  const setSynthesis = useDebateStore((s) => s.setSynthesis)
  const completeIteration = useDebateStore((s) => s.completeIteration)
  const setDirectAnswer = useDebateStore((s) => s.setDirectAnswer)
  const finishDebate = useDebateStore((s) => s.finishDebate)

  const start = useCallback(async (req: MultiAgentChatRequest) => {
    const controller = new AbortController()
    beginRun(controller)

    const debateId = generateUUID()
    startDebate(debateId)

    addMessage({
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
      if (runId) setActiveRunId(runId)

      for await (const event of readSSE(res, controller.signal)) {
        switch (event.type) {
          case 'phase_start':
            setPhase(
              event.phase as DebatePhase,
              (event.iteration as number) ?? 1,
            )
            break

          case 'moderator_init': {
            const init = event.analysis as ModeratorInit | undefined
            if (init) setModeratorInit(init)
            break
          }

          case 'expert_answer':
            setExpertAnswer(
              event.iteration as number,
              event.answer as ExpertAnswer,
            )
            break

          case 'critic_review':
            setCriticReview(
              event.iteration as number,
              event.review as CriticReview,
            )
            break

          case 'moderator_synthesize': {
            const synthesis = event.analysis as ModeratorSynthesis | undefined
            if (synthesis) setSynthesis(event.iteration as number, synthesis)
            break
          }

          case 'iteration_complete':
            completeIteration(event.iteration as number)
            break

          case 'done': {
            const finalAnswer = event.final_answer as string
            const termination = event.termination_reason as TerminationReason
            const total = event.total_iterations as number
            const metrics = event.metrics as StreamMetrics | undefined
            if (event.was_direct_answer) setDirectAnswer()
            finishDebate(termination, total)

            addMessage({
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
            addMessage({
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
        addMessage({
          id: generateUUID(),
          type: 'error',
          role: 'assistant',
          content: (err as Error).message,
        })
      }
    } finally {
      resetRun()
    }
  }, [
    beginRun,
    setActiveRunId,
    resetRun,
    addMessage,
    startDebate,
    setPhase,
    setModeratorInit,
    setExpertAnswer,
    setCriticReview,
    setSynthesis,
    completeIteration,
    setDirectAnswer,
    finishDebate,
  ])

  return { start }
}
