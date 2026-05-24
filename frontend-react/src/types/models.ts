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
