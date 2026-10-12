import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { AuthProvider } from './auth/AuthContext'
import { ReportButton } from './components/ReportButton'
import { ItemForm } from './components/ItemForm'
import { PriceReference } from './components/PriceReference'
import { ReportsPage } from './pages/ReportsPage'
import { MyGiftsPage } from './pages/MyGiftsPage'
import { ItemDetailPage } from './pages/ItemDetailPage'
import type { ReportDetail } from './api/reports'
import type { Gift } from './api/gifts'
import type { Item } from './api/items'

const timestamp = '2026-10-12T00:00:00Z'
const user = { id: 2, nickname: '当前同学', campus: '五山校区', student_no_masked: '***002', created_at: timestamp, is_admin: false }
const row: ReportDetail = { id: 9, target_type: 'item', target_id: 1, reason: '信息虚假', description: '请核查', status: 'dismissed', resolution_note: '证据不足', created_at: timestamp, resolved_at: timestamp, appeal: null, evidence: { title: '共享教材' } }
const gift: Gift = { id: 7, item_id: 1, owner_id: 1, recipient_id: 2, note: '周末交接', status: 'approved', owner_confirmed_at: null, recipient_confirmed_at: null, completed_at: null, created_at: timestamp, updated_at: timestamp, item: { id: 1, title: '免费教材', images: [] }, owner: { id: 1, nickname: '物主同学' }, recipient: { id: 2, nickname: '当前同学' } }
const item: Item = { id: 1, owner_id: 1, title: '免费教材', description: '课程分享', category: '教材资料', campus: '五山校区', mode: 'gift', price_cents: null, borrow_note: null, status: 'published', availability: 'available', images: [], interest_tags: [], owner: gift.owner, created_at: timestamp, updated_at: timestamp }
const fetchMock = vi.fn<typeof fetch>()
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
const reports = (reports: ReportDetail[]) => ({ reports, total: reports.length, page: 1, page_size: 20 })
const gifts = (rows: Gift[]) => ({ gifts: rows, total: rows.length, page: 1, page_size: 20 })

function renderPage(path: string) {
  render(<MemoryRouter initialEntries={[path]}><AuthProvider><Routes>
    <Route path="/my-reports" element={<ReportsPage />} /><Route path="/admin/reports" element={<ReportsPage admin />} />
    <Route path="/my-gifts" element={<MyGiftsPage />} /><Route path="/items/:id" element={<ItemDetailPage />} />
  </Routes></AuthProvider></MemoryRouter>)
}
beforeEach(() => { vi.stubGlobal('fetch', fetchMock); vi.spyOn(window, 'confirm').mockReturnValue(true); fetchMock.mockImplementation(async () => json(user)) })
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); fetchMock.mockReset() })

it('举报入口以真实 API Client 提交，防重复点击，失败反馈清晰', async () => {
  let finish!: (response: Response) => void
  fetchMock.mockImplementation(() => new Promise(resolve => { finish = resolve }))
  render(<MemoryRouter><ReportButton target="message" id={10} /></MemoryRouter>)
  fireEvent.click(screen.getByRole('button', { name: '举报' }))
  fireEvent.change(screen.getByLabelText('详细描述'), { target: { value: '这条消息含不当行为' } })
  const button = screen.getByRole('button', { name: '提交举报' })
  fireEvent.click(button); fireEvent.click(button)
  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(fetchMock.mock.calls[0][1]).toEqual(expect.objectContaining({ credentials: 'include', method: 'POST', body: JSON.stringify({ target_type: 'message', target_id: 10, reason: '信息虚假或违规', description: '这条消息含不当行为' }) }))
  finish(json({ detail: '举报对象不存在或无权访问。' }, 404))
  expect(await screen.findByRole('alert')).toHaveTextContent('举报对象不存在或无权访问')
  fireEvent.click(screen.getByRole('button', { name: '提交举报' }))
  finish(json(row, 201))
  expect(await screen.findByText('举报已提交。')).toBeInTheDocument()
})

it('举报人查看结果并提交一次复核申诉', async () => {
  let current = { ...row }
  fetchMock.mockImplementation(async (url, options) => {
    const path = new URL(String(url)).pathname
    if (path.endsWith('/auth/me')) return json(user)
    if (path.endsWith('/appeal') && options?.method === 'POST') { current = { ...current, appeal: { id: 1, reason: '补充交接情况', status: 'pending', decision: null, review_note: null, created_at: timestamp, reviewed_at: null } }; return json(current) }
    return json(path.endsWith('/mine') ? reports([current]) : current)
  })
  renderPage('/my-reports?report=9')
  expect(await screen.findByText('处理说明：证据不足')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('复核申诉理由（仅可提交一次）'), { target: { value: '补充交接情况' } })
  fireEvent.click(screen.getByRole('button', { name: '提交复核申诉' }))
  expect(await screen.findByText('等待管理员复核')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: '提交复核申诉' })).not.toBeInTheDocument()
})

it('普通用户看不到管理员功能；管理员可记录处理及复核结果', async () => {
  let current: ReportDetail = { ...row, status: 'pending', resolution_note: null, resolved_at: null }
  let admin = false
  fetchMock.mockImplementation(async (url, options) => {
    const path = new URL(String(url)).pathname
    if (path.endsWith('/auth/me')) return json({ ...user, is_admin: admin })
    if (options?.method === 'POST') {
      if (path.endsWith('/resolve')) current = { ...current, status: 'handled', resolution_note: '已人工核查', appeal: { id: 1, reason: '补充证据请求复核', status: 'pending', decision: null, review_note: null, created_at: timestamp, reviewed_at: null } }
      else current = { ...current, appeal: { ...current.appeal!, status: 'reviewed', decision: 'handled', review_note: '已复核并反馈', reviewed_at: timestamp } }
      return json(current)
    }
    return json(path.endsWith('/reports') ? reports([current]) : current)
  })
  const view = render(<MemoryRouter initialEntries={['/admin/reports?report=9']}><AuthProvider><ReportsPage admin /></AuthProvider></MemoryRouter>)
  expect(await screen.findByRole('alert')).toHaveTextContent('仅管理员可以访问')
  expect(fetchMock.mock.calls.filter(([url]) => String(url).includes('/admin/reports'))).toHaveLength(0)
  view.unmount(); admin = true
  renderPage('/admin/reports?report=9')
  fireEvent.change(await screen.findByLabelText('处理说明'), { target: { value: '已人工核查' } })
  fireEvent.click(screen.getByRole('button', { name: '提交处理结果' }))
  await screen.findByRole('button', { name: '提交复核结果' })
  fireEvent.change(await screen.findByLabelText('处理说明'), { target: { value: '已复核并反馈' } })
  fireEvent.click(await screen.findByRole('button', { name: '提交复核结果' }))
  expect(await screen.findByText(/复核结果：已处理 · 已复核并反馈/)).toBeInTheDocument()
})

it('发布免费转赠清空价格和借用说明，详情可提交领取申请', async () => {
  const success = vi.fn()
  fetchMock.mockImplementation(async (url, options) => {
    const path = new URL(String(url)).pathname
    if (path.endsWith('/auth/me')) return json(user)
    if (path.endsWith('/gift-requests')) return json(gift, 201)
    return json(item, options?.method === 'POST' ? 201 : 200)
  })
  const form = render(<ItemForm onSuccess={success} />)
  fireEvent.click(screen.getByRole('button', { name: '免费转赠' }))
  expect(screen.queryByLabelText('售价（元）')).not.toBeInTheDocument()
  expect(screen.queryByLabelText('借用说明')).not.toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('物品名称'), { target: { value: '免费教材' } })
  fireEvent.change(screen.getByLabelText('物品描述'), { target: { value: '课程分享' } })
  fireEvent.click(screen.getByRole('button', { name: '发布物品' }))
  await waitFor(() => expect(success).toHaveBeenCalled())
  const payload = JSON.parse(String(fetchMock.mock.calls[0][1]?.body))
  expect(payload).toMatchObject({ mode: 'gift', price_cents: null, borrow_note: null })
  form.unmount(); renderPage('/items/1')
  fireEvent.change(await screen.findByLabelText('领取备注（选填）'), { target: { value: '周末交接' } })
  fireEvent.click(screen.getByRole('button', { name: '申请领取' }))
  expect(await screen.findByText(/领取申请已提交/)).toBeInTheDocument()
})

it('转赠双方角色按钮正确，同意、单方等待、完成历史按真实响应更新', async () => {
  let current: Gift = { ...gift, owner_id: 2, recipient_id: 3, status: 'pending', owner: { id: 2, nickname: '当前同学' }, recipient: { id: 3, nickname: '领取同学' } }
  fetchMock.mockImplementation(async (url, options) => {
    const parsed = new URL(String(url))
    if (parsed.pathname.endsWith('/auth/me')) return json(user)
    if (options?.method === 'POST') { current = parsed.pathname.endsWith('/approve') ? { ...current, status: 'approved' } : { ...current, owner_confirmed_at: timestamp }; return json(current) }
    return json(gifts(parsed.searchParams.get('role') === 'owner' ? [current] : []))
  })
  renderPage('/my-gifts')
  fireEvent.click(await screen.findByRole('button', { name: '我赠出的' }))
  fireEvent.click(await screen.findByRole('button', { name: '同意领取' }))
  fireEvent.click(await screen.findByRole('button', { name: '确认已交付物品' }))
  expect(await screen.findByText('你的交接确认已记录，等待对方确认。')).toBeInTheDocument()
  await waitFor(() => expect(screen.queryByRole('button', { name: '取消待交接' })).not.toBeInTheDocument())
  current = { ...current, recipient_confirmed_at: timestamp, completed_at: timestamp, status: 'completed' }
  fireEvent.click(screen.getByRole('button', { name: '刷新转赠' }))
  expect(await screen.findByText('转赠完成')).toBeInTheDocument()
  expect(screen.getByText(/完成时间/)).toBeInTheDocument()
})

it('挂牌价格参考显示真实响应范围和限定说明，同校区不足时不显示范围', async () => {
  const samples = [{ id: 2, title: '教材甲', price_cents: 1000, campus: '五山校区' }, { id: 3, title: '教材乙', price_cents: 2000, campus: '五山校区' }, { id: 4, title: '教材丙', price_cents: 3000, campus: '大学城校区' }]
  fetchMock.mockImplementation(async url => String(url).includes('same_campus=true') ? json({ items: samples.slice(0, 2), sample_count: 2, min_price_cents: null, max_price_cents: null }) : json({ items: samples, sample_count: 3, min_price_cents: 1000, max_price_cents: 3000 }))
  render(<MemoryRouter><PriceReference itemId={1} /></MemoryRouter>)
  expect(await screen.findByText('所列 3 件挂牌价范围：¥10.00～¥30.00')).toBeInTheDocument()
  expect(screen.getByText('仅供参考，展示的是当前挂牌价，不代表实际成交价或公允价格。')).toBeInTheDocument()
  expect(within(screen.getByLabelText('挂牌价格参考')).getByRole('link', { name: '教材甲' })).toHaveAttribute('href', '/items/2')
  fireEvent.click(screen.getByRole('checkbox', { name: '仅看同校区' }))
  expect(await screen.findByText('参考数据不足')).toBeInTheDocument()
  expect(screen.queryByText(/挂牌价范围：/)).not.toBeInTheDocument()
})
