import { env } from '../config/env'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const unauthorizedListeners = new Set<() => void>()

export function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : '暂时无法连接服务器，请检查网络或稍后重试。'
}

// Share transport, cookies, timeout and cancellation across REST endpoints.
async function request(path: string, method: 'GET' | 'POST' | 'PATCH' | 'DELETE', body?: unknown, signal?: AbortSignal): Promise<unknown> {
  const controller = new AbortController()
  const abort = () => controller.abort()
  if (signal?.aborted) abort()
  signal?.addEventListener('abort', abort, { once: true })
  const timer = window.setTimeout(abort, 5000)

  try {
    const response = await fetch(`${env.apiBaseUrl}${path}`, {
      method,
      credentials: 'include',
      headers: { Accept: 'application/json', ...(!(body instanceof FormData) && body !== undefined ? { 'Content-Type': 'application/json' } : {}) },
      ...(body !== undefined ? { body: body instanceof FormData ? body : JSON.stringify(body) } : {}),
      signal: controller.signal,
    })
    if (!response.ok) {
      const data: unknown = await response.json().catch(() => null)
      const detail = typeof data === 'object' && data !== null && 'detail' in data ? data.detail : null
      const message = response.status === 422 ? '填写的信息不符合要求，请检查输入。'
        : typeof detail === 'string' ? detail : '请求暂时无法完成，请稍后重试。'
      if (response.status === 401 && path !== '/auth/login' && !controller.signal.aborted) unauthorizedListeners.forEach(listener => listener())
      throw new ApiError(response.status, message)
    }
    if (response.status === 204) return undefined
    return await response.json()
  } finally {
    window.clearTimeout(timer)
    signal?.removeEventListener('abort', abort)
  }
}

export const apiClient = {
  get: (path: string, signal?: AbortSignal) => request(path, 'GET', undefined, signal),
  post: (path: string, body?: unknown, signal?: AbortSignal) => request(path, 'POST', body, signal),
  patch: (path: string, body?: unknown, signal?: AbortSignal) => request(path, 'PATCH', body, signal),
  delete: (path: string, signal?: AbortSignal) => request(path, 'DELETE', undefined, signal),
  onUnauthorized: (listener: () => void) => {
    unauthorizedListeners.add(listener)
    return () => { unauthorizedListeners.delete(listener) }
  },
}
