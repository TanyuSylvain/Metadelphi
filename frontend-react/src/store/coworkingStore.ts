import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { CoworkingRound, ToolCall, FileRecord } from '../types/coworking'
import { generateUUID } from '../utils/uuid'

interface CoworkingState {
  workspacePath: string
  planSteps: string[]
  rounds: CoworkingRound[]
  generatedFiles: FileRecord[]
  deletedFiles: string[]
  finalAnswer: string

  setWorkspacePath: (path: string) => void
  setPlanSteps: (steps: string[]) => void
  startRound: (round: number) => void
  appendReasoning: (round: number, chunk: string) => void
  startTool: (round: number, tool: string, input: Record<string, unknown>) => string
  finishTool: (round: number, toolId: string, result: string) => void
  failTool: (round: number, toolId: string, error: string) => void
  completeRound: (round: number, status: 'done' | 'error') => void
  addGeneratedFile: (file: FileRecord) => void
  addDeletedFile: (path: string) => void
  setFinalAnswer: (text: string) => void
  appendFinalAnswer: (chunk: string) => void
  reset: () => void
}

export const useCoworkingStore = create<CoworkingState>()(
  persist(
    (set) => ({
      workspacePath: '',
      planSteps: [],
      rounds: [],
      generatedFiles: [],
      deletedFiles: [],
      finalAnswer: '',

      setWorkspacePath: (path) => set({ workspacePath: path }),

      setPlanSteps: (steps) => set({ planSteps: steps }),

      startRound: (round) =>
        set((s) => ({
          rounds: [
            ...s.rounds,
            { round, reasoning: '', toolCalls: [], status: 'running' },
          ],
        })),

      appendReasoning: (round, chunk) =>
        set((s) => ({
          rounds: s.rounds.map((r) =>
            r.round === round ? { ...r, reasoning: r.reasoning + chunk } : r,
          ),
        })),

      startTool: (round, tool, input) => {
        const id = generateUUID()
        const toolCall: ToolCall = { id, tool, input, status: 'running' }
        set((s) => ({
          rounds: s.rounds.map((r) =>
            r.round === round ? { ...r, toolCalls: [...r.toolCalls, toolCall] } : r,
          ),
        }))
        return id
      },

      finishTool: (round, toolId, result) =>
        set((s) => ({
          rounds: s.rounds.map((r) =>
            r.round === round
              ? {
                  ...r,
                  toolCalls: r.toolCalls.map((tc) =>
                    tc.id === toolId ? { ...tc, status: 'done', result } : tc,
                  ),
                }
              : r,
          ),
        })),

      failTool: (round, toolId, error) =>
        set((s) => ({
          rounds: s.rounds.map((r) =>
            r.round === round
              ? {
                  ...r,
                  toolCalls: r.toolCalls.map((tc) =>
                    tc.id === toolId ? { ...tc, status: 'error', result: error } : tc,
                  ),
                }
              : r,
          ),
        })),

      completeRound: (round, status) =>
        set((s) => ({
          rounds: s.rounds.map((r) => (r.round === round ? { ...r, status } : r)),
        })),

      addGeneratedFile: (file) =>
        set((s) => ({ generatedFiles: [...s.generatedFiles, file] })),

      addDeletedFile: (path) =>
        set((s) => ({ deletedFiles: [...s.deletedFiles, path] })),

      setFinalAnswer: (text) => set({ finalAnswer: text }),

      appendFinalAnswer: (chunk) =>
        set((s) => ({ finalAnswer: s.finalAnswer + chunk })),

      reset: () =>
        set({
          planSteps: [],
          rounds: [],
          generatedFiles: [],
          deletedFiles: [],
          finalAnswer: '',
        }),
    }),
    {
      name: 'metadelphi-coworking',
      partialize: (s) => ({ workspacePath: s.workspacePath }),
    },
  ),
)
