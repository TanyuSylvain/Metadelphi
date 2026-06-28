import { create } from 'zustand'

interface AppState {
  isProcessing: boolean
  activeRunId: string | null
  abortController: AbortController | null
  settingsOpen: boolean
  configOpen: boolean

  beginRun: (controller: AbortController) => void
  setActiveRunId: (id: string | null) => void
  resetRun: () => void
  setSettingsOpen: (open: boolean) => void
  setConfigOpen: (open: boolean) => void
  cancel: () => void
}

export const useAppStore = create<AppState>((set, get) => ({
  isProcessing: false,
  activeRunId: null,
  abortController: null,
  settingsOpen: false,
  configOpen: false,

  beginRun: (controller) =>
    set({ isProcessing: true, abortController: controller, activeRunId: null }),

  setActiveRunId: (id) => set({ activeRunId: id }),

  resetRun: () =>
    set({ isProcessing: false, activeRunId: null, abortController: null }),

  setSettingsOpen: (open) => set({ settingsOpen: open }),

  setConfigOpen: (open) => set({ configOpen: open }),

  cancel: () => {
    const { abortController, activeRunId } = get()
    abortController?.abort()
    if (activeRunId) {
      fetch(`/chat/runs/${activeRunId}/cancel`, { method: 'POST' }).catch(() => {})
    }
    set({ isProcessing: false, activeRunId: null, abortController: null })
  },
}))
