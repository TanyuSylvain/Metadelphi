import { api } from './client'
import type { AppConfig, Model, ProviderSettings } from '../types/models'
import type { SearchEngineStatus, SearchEngineUpdateRequest } from '../types/api'

export interface ModelsResponse {
  models: Model[]
  count: number
}

export interface ProviderSettingsResponse {
  providers: Record<string, ProviderSettings>
}

export interface ProviderTestResponse {
  success: boolean
  message: string
  latency_ms: number | null
}

export interface ProviderModelTestRequest {
  provider_id: string
  model_id: string
  api_key: string
  base_url?: string
  is_image_model: boolean
}

export interface ConfigResponse {
  config: AppConfig
}

export interface ConfigUpdateResponse {
  success: boolean
  message: string
  errors?: string[]
}

export const modelsApi = {
  list: () => api.get<ModelsResponse>('/models/'),

  getProviderSettings: () => api.get<ProviderSettingsResponse>('/settings/providers'),

  testProvider: (providerId: string) =>
    api.post<ProviderTestResponse>(`/settings/providers/${providerId}/test`),

  testProviderModel: (request: ProviderModelTestRequest) =>
    api.post<ProviderTestResponse>('/settings/providers/test-model', request),

  getConfig: () => api.get<ConfigResponse>('/settings/config'),

  updateConfig: (config: AppConfig) =>
    api.put<ConfigUpdateResponse>('/settings/config', { config }),

  getSearchEngineStatus: () => api.get<SearchEngineStatus>('/settings/search-engine'),

  updateSearchEngine: (data: SearchEngineUpdateRequest) =>
    api.put<{ success: boolean; message: string; default: 'bailian' | 'tavily' }>(
      '/settings/search-engine',
      data,
    ),
}
