import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AppRoutes from '../AppRoutes'
import { apiClient } from '../api/client'
import type { CurrentUser } from '../api/auth'

const currentUser: CurrentUser = {
  id: 1, nickname: '易享同学', campus: '五山校区', created_at: '2026-10-12T00:00:00Z', student_no_masked: '********0346',
}
const fetchMock = vi.fn<typeof fetch>()
let restoredUser: CurrentUser | null

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
}

function renderPath(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><AppRoutes /></MemoryRouter>)
}

function fillRegistration() {
  fireEvent.change(screen.getByLabelText('昵称'), { target: { value: ' 易享同学 ' } })
  fireEvent.change(screen.getByLabelText('学号'), { target: { value: ' TEST_2026_001 ' } })
  fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'Test-only-password-123' } })
  fireEvent.change(screen.getByLabelText('所属校区'), { target: { value: '五山校区' } })
}

function fillLogin() {
  fireEvent.change(screen.getByLabelText('学号'), { target: { value: 'TEST_2026_001' } })
  fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'Test-only-password-123' } })
}

beforeEach(() => {
  restoredUser = null
  fetchMock.mockImplementation(async (url) => {
    const path = String(url)
    if (path.endsWith('/auth/me')) return restoredUser ? json(restoredUser) : json({ detail: '登录已失效，请重新登录。' }, 401)
    if (path.endsWith('/auth/register')) return json({ id: 1, nickname: currentUser.nickname, campus: currentUser.campus, created_at: currentUser.created_at }, 201)
    if (path.endsWith('/auth/login')) return json(currentUser)
    if (path.endsWith('/auth/logout')) return new Response(null, { status: 204 })
    return json({ status: 'ok' })
  })
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
  fetchMock.mockReset()
})

describe('Phase 1 用户系统', () => {
  it('注册页面只包含四项输入并说明学号不是官方认证', async () => {
    renderPath('/register')
    expect(screen.getByRole('heading', { name: '加入华园易享' })).toBeInTheDocument()
    expect(document.querySelectorAll('form input, form select')).toHaveLength(4)
    expect(screen.getByText('学号由用户自行填写，不代表已完成官方校园身份认证。')).toBeInTheDocument()
    expect(screen.getAllByRole('option')).toHaveLength(4)
    await screen.findByRole('link', { name: '登录' })
  })

  it('无效注册不会提交，并给出中文字段提示', async () => {
    renderPath('/register')
    fireEvent.click(screen.getByRole('button', { name: '注册账号' }))
    expect(screen.getByText('昵称需为 2～30 个字符。')).toBeInTheDocument()
    expect(screen.getByText('密码需为 8～128 个字符。')).toBeInTheDocument()
    expect(screen.getByText('请选择所属校区。')).toBeInTheDocument()
    expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/auth/register'))).toHaveLength(0)
    await screen.findByRole('link', { name: '登录' })
  })

  it('注册成功后跳转登录，提交修剪后的账号与昵称', async () => {
    renderPath('/register')
    fillRegistration()
    fireEvent.click(screen.getByRole('button', { name: '注册账号' }))
    expect(await screen.findByText('注册成功，请使用学号和密码登录。')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '欢迎回来' })).toBeInTheDocument()
    const registration = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/auth/register'))
    expect(JSON.parse(String(registration?.[1]?.body))).toMatchObject({ nickname: '易享同学', student_no: 'TEST_2026_001' })
    expect(registration?.[1]?.credentials).toBe('include')
  })

  it('重复学号错误清晰显示，保留注册页面', async () => {
    fetchMock.mockImplementation(async url => String(url).endsWith('/auth/register')
      ? json({ detail: '该学号已注册，请登录或使用其他账号。' }, 409) : json({ detail: '未登录' }, 401))
    renderPath('/register')
    fillRegistration()
    fireEvent.click(screen.getByRole('button', { name: '注册账号' }))
    expect(await screen.findByText('该学号已注册，请登录或使用其他账号。')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '加入华园易享' })).toBeInTheDocument()
  })

  it('登录成功跳转首页并显示昵称，不存储认证令牌', async () => {
    const storageSpy = vi.spyOn(Storage.prototype, 'setItem')
    renderPath('/login')
    fillLogin()
    fireEvent.click(screen.getByRole('button', { name: '登录' }))
    await screen.findByRole('heading', { level: 1, name: /校园互助/ })
    expect(screen.getByText('易享同学')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('校园互助')
    expect(screen.getByRole('link', { name: '个人中心' })).toBeInTheDocument()
    expect(storageSpy).not.toHaveBeenCalled()
  })

  it('错误凭证显示统一提示', async () => {
    fetchMock.mockImplementation(async () => json({ detail: '学号或密码错误。' }, 401))
    renderPath('/login')
    fillLogin()
    fireEvent.click(screen.getByRole('button', { name: '登录' }))
    expect(await screen.findByText('学号或密码错误。')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '欢迎回来' })).toBeInTheDocument()
  })

  it('网络错误不会被描述为密码错误', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))
    renderPath('/login')
    fillLogin()
    fireEvent.click(screen.getByRole('button', { name: '登录' }))
    await waitFor(() => expect(screen.getAllByText('暂时无法连接服务器，请检查网络或稍后重试。').length).toBeGreaterThan(0))
    expect(screen.queryByText('学号或密码错误。')).not.toBeInTheDocument()
  })

  it('未登录访问个人中心跳转登录，且没有循环请求', async () => {
    renderPath('/profile')
    expect(await screen.findByRole('heading', { name: '欢迎回来' })).toBeInTheDocument()
    expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/auth/me'))).toHaveLength(1)
  })

  it('刷新初始化恢复有效身份，个人中心只展示脱敏学号', async () => {
    restoredUser = currentUser
    renderPath('/profile')
    expect(await screen.findByText('********0346')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '个人中心' })).toBeInTheDocument()
    expect(screen.getByText('五山校区')).toBeInTheDocument()
    expect(screen.queryByText('TEST_2026_001')).not.toBeInTheDocument()
    expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/auth/me'))).toHaveLength(1)
  })

  it('切换首页和个人中心不重复恢复身份', async () => {
    restoredUser = currentUser
    renderPath('/')
    fireEvent.click(await screen.findByRole('link', { name: '个人中心' }))
    expect(await screen.findByText('********0346')).toBeInTheDocument()
    expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/auth/me'))).toHaveLength(1)
  })

  it('退出成功后更新状态，隐藏私有页面和昵称', async () => {
    restoredUser = currentUser
    renderPath('/profile')
    fireEvent.click(await screen.findByRole('button', { name: '退出登录' }))
    expect(await screen.findByRole('heading', { name: '欢迎回来' })).toBeInTheDocument()
    expect(screen.queryByText('********0346')).not.toBeInTheDocument()
    expect(screen.queryByText('易享同学')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: '注册' })).toBeInTheDocument()
  })

  it('恢复身份网络失败时保留重试入口，恢复后进入个人中心', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Offline'))
    renderPath('/profile')
    expect(await screen.findByRole('button', { name: '重新连接' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '欢迎回来' })).not.toBeInTheDocument()
    restoredUser = currentUser
    fireEvent.click(screen.getByRole('button', { name: '重新连接' }))
    expect(await screen.findByText('********0346')).toBeInTheDocument()
  })

  it('登出网络失败时不伪装成已退出', async () => {
    restoredUser = currentUser
    const baseMock = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation((url, options) => String(url).endsWith('/auth/logout')
      ? Promise.reject(new TypeError('Offline')) : baseMock(url, options))
    renderPath('/profile')
    fireEvent.click(await screen.findByRole('button', { name: '退出登录' }))
    expect(await screen.findByText('暂时无法连接服务器，请检查网络或稍后重试。')).toBeInTheDocument()
    expect(screen.getByText('********0346')).toBeInTheDocument()
  })

  it('会话失效统一清除身份并转到登录页', async () => {
    restoredUser = currentUser
    renderPath('/profile')
    await screen.findByText('********0346')
    restoredUser = null
    await act(async () => { await apiClient.get('/auth/me').catch(() => undefined) })
    expect(await screen.findByRole('heading', { name: '欢迎回来' })).toBeInTheDocument()
    expect(screen.getByText('登录已过期，请重新登录。')).toBeInTheDocument()
  })

  it('提交过程中禁用按钮，避免重复点击登录', async () => {
    const baseMock = fetchMock.getMockImplementation()!
    let resolveLogin!: (response: Response) => void
    fetchMock.mockImplementation((url, options) => String(url).endsWith('/auth/login')
      ? new Promise(resolve => { resolveLogin = resolve }) : baseMock(url, options))
    renderPath('/login')
    fillLogin()
    fireEvent.click(screen.getByRole('button', { name: '登录' }))
    const pending = screen.getByRole('button', { name: '正在登录…' })
    expect(pending).toBeDisabled()
    fireEvent.click(pending)
    expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/auth/login'))).toHaveLength(1)
    await act(async () => resolveLogin(json(currentUser)))
    expect(await screen.findByText('易享同学')).toBeInTheDocument()
  })

  it('迟到的匿名恢复响应不会覆盖新的登录身份', async () => {
    const baseMock = fetchMock.getMockImplementation()!
    let resolveMe!: (response: Response) => void
    fetchMock.mockImplementation((url, options) => String(url).endsWith('/auth/me')
      ? new Promise(resolve => { resolveMe = resolve }) : baseMock(url, options))
    renderPath('/login')
    fillLogin()
    fireEvent.click(screen.getByRole('button', { name: '登录' }))
    await screen.findByRole('heading', { level: 1, name: /校园互助/ })
    expect(screen.getByText('易享同学')).toBeInTheDocument()
    await act(async () => resolveMe(json({ detail: '未登录' }, 401)))
    expect(screen.getByRole('link', { name: '个人中心' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '注册' })).not.toBeInTheDocument()
  })
})
