import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ChatMode = 'simple' | 'debate' | 'coworking'

export interface MultiAgentConfig {
  moderator: string
  expert: string
  critic: string
  maxIterations: number
  scoreThreshold: number
  thinking: {
    moderator: boolean
    expert: boolean
    critic: boolean
  }
}

const DEFAULT_MA_CONFIG: MultiAgentConfig = {
  moderator: '',
  expert: '',
  critic: '',
  maxIterations: 3,
  scoreThreshold: 80,
  thinking: { moderator: false, expert: false, critic: false },
}

interface PrefsState {
  selectedModel: string
  chatMode: ChatMode
  thinkingEnabledByModel: Record<string, boolean>
  markdownEnabled: boolean
  webSearchEnabled: boolean
  debatePanelVisible: boolean
  imageModeEnabled: boolean
  imageAspectRatio: string
  sidebarCollapsed: boolean
  sidebarWidth: number
  panelRatio: number
  multiAgentConfig: MultiAgentConfig

  setSelectedModel: (model: string) => void
  setChatMode: (mode: ChatMode) => void
  setThinkingEnabled: (modelId: string, enabled: boolean) => void
  setMarkdownEnabled: (v: boolean) => void
  setWebSearchEnabled: (v: boolean) => void
  setDebatePanelVisible: (v: boolean) => void
  setImageModeEnabled: (v: boolean) => void
  setImageAspectRatio: (ratio: string) => void
  setSidebarCollapsed: (v: boolean) => void
  setSidebarWidth: (w: number) => void
  setPanelRatio: (r: number) => void
  setMultiAgentConfig: (cfg: Partial<MultiAgentConfig>) => void
  isThinkingEnabled: (modelId: string) => boolean
}

export const usePrefsStore = create<PrefsState>()(
  persist(
    (set, get) => ({
      selectedModel: '',
      chatMode: 'simple',
      thinkingEnabledByModel: {},
      markdownEnabled: true,
      webSearchEnabled: false,
      debatePanelVisible: true,
      imageModeEnabled: false,
      imageAspectRatio: '1:1',
      sidebarCollapsed: false,
      sidebarWidth: 240,
      panelRatio: 0.55,
      multiAgentConfig: DEFAULT_MA_CONFIG,

      setSelectedModel: (model) => set({ selectedModel: model }),
      setChatMode: (mode) => set({ chatMode: mode }),
      setThinkingEnabled: (modelId, enabled) =>
        set((s) => ({
          thinkingEnabledByModel: { ...s.thinkingEnabledByModel, [modelId]: enabled },
        })),
      setMarkdownEnabled: (v) => set({ markdownEnabled: v }),
      setWebSearchEnabled: (v) => set({ webSearchEnabled: v }),
      setDebatePanelVisible: (v) => set({ debatePanelVisible: v }),
      setImageModeEnabled: (v) => set({ imageModeEnabled: v }),
      setImageAspectRatio: (ratio) => set({ imageAspectRatio: ratio }),
      setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),
      setSidebarWidth: (w) => set({ sidebarWidth: w }),
      setPanelRatio: (r) => set({ panelRatio: r }),
      setMultiAgentConfig: (cfg) =>
        set((s) => ({ multiAgentConfig: { ...s.multiAgentConfig, ...cfg } })),
      isThinkingEnabled: (modelId) => get().thinkingEnabledByModel[modelId] ?? false,
    }),
    { name: 'metadelphi-prefs' },
  ),
)
