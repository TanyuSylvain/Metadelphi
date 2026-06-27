export interface ChatRequest {
  message: string
  conversation_id?: string
  model?: string
  thinking?: boolean
  web_search?: boolean
  aspect_ratio?: string
  image_action?: 'generate' | 'edit'
  edit_source_image?: {
    data: string
    mime_type: string
    index?: number
  }
}

export interface MultiAgentModelConfig {
  moderator?: string
  expert?: string
  critic?: string
}

export interface MultiAgentThinkingConfig {
  moderator: boolean
  expert: boolean
  critic: boolean
}

export interface MultiAgentChatRequest {
  message: string
  conversation_id?: string
  models?: MultiAgentModelConfig
  max_iterations?: number
  score_threshold?: number
  thinking?: MultiAgentThinkingConfig
}

export interface CoworkingChatRequest {
  message: string
  conversation_id?: string
  model?: string
  workspace_path: string
  thinking?: boolean
  web_search?: boolean
  max_iterations?: number
}

export interface ProviderUpdateEntry {
  api_key?: string
  base_url?: string
}

export interface SearchEngineStatus {
  default: 'bailian' | 'tavily'
  available: Record<'bailian' | 'tavily', boolean>
  configured: boolean
}

export interface SearchEngineUpdateRequest {
  default: 'bailian' | 'tavily'
}

export interface SwitchModeRequest {
  target_mode: 'simple' | 'debate' | 'coworking'
  debate_config?: {
    moderator?: string
    expert?: string
    critic?: string
    max_iterations?: number
    score_threshold?: number
  }
}
