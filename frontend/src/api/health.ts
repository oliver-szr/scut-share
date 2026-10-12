import { apiClient } from './client'

export interface HealthResponse {
  status: 'ok'
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const data = await apiClient.get('/health', signal)
  if (typeof data !== 'object' || data === null || !('status' in data) || data.status !== 'ok') {
    throw new Error('Unexpected health response')
  }
  return { status: 'ok' }
}
