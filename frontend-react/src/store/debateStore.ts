import { create } from 'zustand'
import type { DebateIteration, ModeratorInit, DebatePhase, TerminationReason } from '../types/debate'
import type { ExpertAnswer, CriticReview } from '../types/debate'

interface DebateState {
  currentDebateId: string | null
  moderatorInit: ModeratorInit | null
  iterations: DebateIteration[]
  currentPhase: DebatePhase
  currentIteration: number
  isDirectAnswer: boolean
  expandedCard: 'init' | number | null
  termination: TerminationReason
  totalIterations: number

  startDebate: (debateId: string) => void
  setModeratorInit: (init: ModeratorInit) => void
  setPhase: (phase: DebatePhase, iteration: number) => void
  setExpertAnswer: (iteration: number, answer: ExpertAnswer) => void
  setCriticReview: (iteration: number, review: CriticReview) => void
  completeIteration: (iteration: number) => void
  setDirectAnswer: () => void
  finishDebate: (termination: TerminationReason, total: number) => void
  setExpandedCard: (card: 'init' | number | null) => void
  reset: () => void
}

export const useDebateStore = create<DebateState>((set) => ({
  currentDebateId: null,
  moderatorInit: null,
  iterations: [],
  currentPhase: null,
  currentIteration: 1,
  isDirectAnswer: false,
  expandedCard: null,
  termination: null,
  totalIterations: 0,

  startDebate: (debateId) =>
    set({
      currentDebateId: debateId,
      moderatorInit: null,
      iterations: [],
      currentPhase: null,
      currentIteration: 1,
      isDirectAnswer: false,
      expandedCard: null,
      termination: null,
      totalIterations: 0,
    }),

  setModeratorInit: (init) => set({ moderatorInit: init }),

  setPhase: (phase, iteration) => set({ currentPhase: phase, currentIteration: iteration }),

  setExpertAnswer: (iteration, answer) =>
    set((s) => {
      const existing = s.iterations.find((i) => i.round === iteration)
      if (existing) {
        return {
          iterations: s.iterations.map((i) =>
            i.round === iteration ? { ...i, expert: answer } : i,
          ),
        }
      }
      return { iterations: [...s.iterations, { round: iteration, expert: answer }] }
    }),

  setCriticReview: (iteration, review) =>
    set((s) => ({
      iterations: s.iterations.map((i) =>
        i.round === iteration ? { ...i, critic: review } : i,
      ),
    })),

  completeIteration: (iteration) =>
    set((_s) => ({
      expandedCard: iteration,
      currentIteration: iteration + 1,
    })),

  setDirectAnswer: () => set({ isDirectAnswer: true }),

  finishDebate: (termination, total) =>
    set({ currentPhase: null, termination, totalIterations: total }),

  setExpandedCard: (card) => set({ expandedCard: card }),

  reset: () =>
    set({
      currentDebateId: null,
      moderatorInit: null,
      iterations: [],
      currentPhase: null,
      currentIteration: 1,
      isDirectAnswer: false,
      expandedCard: null,
      termination: null,
      totalIterations: 0,
    }),
}))
