import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { env } from './config/env'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'

const fetchMock = vi.fn<typeof fetch>()

function renderHome() {
  return render(<MemoryRouter><AuthProvider><App /></AuthProvider></MemoryRouter>)
}

function healthRequests() {
  return fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/health'))
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  fetchMock.mockImplementation(async url => new Response(JSON.stringify(
    String(url).endsWith('/auth/me') ? { detail: '登录已失效，请重新登录。' } : { status: 'ok' },
  ), { status: String(url).endsWith('/auth/me') ? 401 : 200, headers: { 'Content-Type': 'application/json' } }))
})

afterEach(() => {
  vi.unstubAllGlobals()
  fetchMock.mockReset()
})

describe('华园易享首页', () => {
  it('展示并列入口并连接到真实物品广场', async () => {
    renderHome()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('校园互助')
    expect(screen.getByRole('heading', { name: '二手交易' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '免费借还' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /二手交易 · 浏览二手出售/ })).toHaveAttribute('href', '/items?mode=sale')
    expect(screen.getByRole('button', { name: /免费借还 · 浏览免费借还/ })).toHaveAttribute('href', '/items?mode=borrow')
    expect(screen.getByRole('link', { name: /发布物品/ })).toHaveAttribute('href', '/items/new')
    expect(await screen.findByText('后端已连接')).toBeInTheDocument()
  })

  it('通过统一 API Client 请求真实配置的健康接口', async () => {
    renderHome()
    expect(await screen.findByText('后端已连接')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(`${env.apiBaseUrl}/health`, expect.objectContaining({
      method: 'GET', signal: expect.any(AbortSignal),
    }))
  })

  it('网络失败时显示失败状态，并允许重试恢复', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    renderHome()
    expect(await screen.findByText('暂时无法连接后端')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '重试' }))
    expect(await screen.findByText('后端已连接')).toBeInTheDocument()
    expect(healthRequests()).toHaveLength(2)
  })

  it('HTTP 错误不会被显示为已连接', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 503 }))
    renderHome()
    expect(await screen.findByText('暂时无法连接后端')).toBeInTheDocument()
    expect(screen.queryByText('后端已连接')).not.toBeInTheDocument()
  })

  it('无效健康响应不会被显示为已连接', async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ status: 'unknown' }), { status: 200 }))
    renderHome()
    expect(await screen.findByText('暂时无法连接后端')).toBeInTheDocument()
  })

  it('组件卸载时取消未完成的请求', async () => {
    fetchMock.mockImplementationOnce(() => new Promise(() => {}))
    const { unmount } = renderHome()
    await waitFor(() => expect(healthRequests()).toHaveLength(1))
    const options = healthRequests()[0][1]
    unmount()
    expect(options?.signal?.aborted).toBe(true)
  })
})
