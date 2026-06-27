import { api } from './client'
import type { Model, ProviderSettings } from '../types/models'
import type { ProviderUpdateEntry, SearchEngineStatus, SearchEngineUpdateRequest } from '../types/api'

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

export const modelsApi = {
  list: () => api.get<ModelsResponse>('/models/'),

  getProviderSettings: () => api.get<ProviderSettingsResponse>('/settings/providers'),

  updateProviderSettings: (providers: Record<string, ProviderUpdateEntry>) =>
    api.put<{ success: boolean; message: string; providers_updated: string[] }>(
      '/settings/providers',
      { providers },
    ),

  testProvider: (providerId: string) =>
    api.post<ProviderTestResponse>(`/settings/providers/${providerId}/test`),

  getSearchEngineStatus: () => api.get<SearchEngineStatus>('/settings/search-engine'),

  updateSearchEngine: (data: SearchEngineUpdateRequest) =>
    api.put<{ success: boolean; message: string; default: 'bailian' | 'tavily' }>(
      '/settings/search-engine',
      data,
    ),
}
