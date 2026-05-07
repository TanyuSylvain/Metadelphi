import { create } from 'zustand'

interface AppState {
  isProcessing: boolean
  activeRunId: string | null
  abortController: AbortController | null
  settingsOpen: boolean

  beginRun: (controller: AbortController) => void
  setActiveRunId: (id: string | null) => void
  resetRun: () => void
  setSettingsOpen: (open: boolean) => void
  cancel: () => void
}

export const useAppStore = create<AppState>((set, get) => ({
  isProcessing: false,
  activeRunId: null,
  abortController: null,
  settingsOpen: false,

  beginRun: (controller) =>
    set({ isProcessing: true, abortController: controller, activeRunId: null }),

  setActiveRunId: (id) => set({ activeRunId: id }),

  resetRun: () =>
    set({ isProcessing: false, activeRunId: null, abortController: null }),

  setSettingsOpen: (open) => set({ settingsOpen: open }),

  cancel: () => {
    const { abortController, activeRunId } = get()
    abortController?.abort()
    if (activeRunId) {
      fetch(`/chat/runs/${activeRunId}/cancel`, { method: 'POST' }).catch(() => {})
    }
    set({ isProcessing: false, activeRunId: null, abortController: null })
  },
}))
