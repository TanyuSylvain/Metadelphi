import { api } from './client'

export const coworkingApi = {
  selectWorkspace: () =>
    api.get<{ path: string | null }>('/chat/coworking/select-workspace'),

  cancelRun: (runId: string) =>
    api.post<unknown>(`/chat/runs/${runId}/cancel`),
}
