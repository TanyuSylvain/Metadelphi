export interface Model {
  provider: string
  provider_name: string
  model_id: string
  model_ref: string
  model_name: string
  description: string
  supports_thinking: boolean
  thinking_locked: boolean
  is_image_model: boolean
}

export interface ProviderInfo {
  name: string
  provider_id: string
  models: { model_id: string; model_name: string; description: string }[]
  supports_streaming: boolean
}

export interface ModelConfig {
  id: string
  supports_thinking: boolean
  thinking_locked: boolean
  is_image_model: boolean
}

export interface ProviderConfig {
  api_key: string | null
  base_url: string | null
  has_base_url: boolean
  display_name: string
  console_url: string
  default_base_url: string | null
  category: string
  models: ModelConfig[]
}

export interface WebSearchConfig {
  default_engine: 'bailian' | 'tavily'
  bailian_api_key: string | null
  tavily_api_key: string | null
}

export interface McpServerConfig {
  name: string
  url: string
  transport: 'sse' | 'stdio'
  api_key_env: string | null
  headers?: Record<string, string>
}

export interface AgentControlConfig {
  max_tool_concurrency: number
  simple_max_tool_iterations: number
  coworking_max_tool_iterations: number
}

export interface AppConfig {
  general: Record<string, unknown>
  agents: AgentControlConfig
  web_search: WebSearchConfig
  mcp: { servers: McpServerConfig[] }
  providers: Record<string, ProviderConfig>
}

export interface ProviderSettings {
  api_key_masked: string | null
  api_key_set: boolean
  base_url: string | null
  has_base_url: boolean
  display_name: string
  console_url: string
  default_base_url: string | null
  test_model: string
  category: string
}

export interface ConversationInfo {
  id: string
  model: string
  mode: 'simple' | 'debate' | 'coworking'
  created_at: string
  updated_at: string
  message_count: number
  title: string
  metadata: {
    mode_history?: string[]
    [key: string]: unknown
  }
}
