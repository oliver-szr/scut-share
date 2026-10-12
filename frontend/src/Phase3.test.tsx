import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { AuthProvider } from './auth/AuthContext'
import type { Item } from './api/items'
import type { Trade } from './api/trades'
import { ItemDetailPage } from './pages/ItemDetailPage'
import { MyTradesPage } from './pages/MyTradesPage'

const timestamp = '2026-10-12T00:00:00Z'
const user = { id: 2, nickname: '当前同学', campus: '五山校区', student_no_masked: '***002', created_at: timestamp }
const item: Item = {
  id: 1, owner_id: 1, title: '课程相机', description: '课程使用', mode: 'sale', category: '数码配件', campus: '五山校区',
  price_cents: 1200, borrow_note: null, status: 'published', availability: 'available', interest_tags: [], images: [],
  owner: { id: 1, nickname: '卖家同学' }, created_at: timestamp, updated_at: timestamp,
}
const initialTrade: Trade = {
  id: 7, item_id: 1, buyer_id: 2, seller_id: 1, price_cents_snapshot: 1200, note: '周五交接', status: 'pending',
  buyer_confirmed_at: null, seller_confirmed_at: null, completed_at: null, created_at: timestamp, updated_at: timestamp,
  item: { id: 1, title: '课程相机', images: [] }, buyer: { id: 2, nickname: '当前同学' }, seller: { id: 1, nickname: '卖家同学' },
}
const fetchMock = vi.fn<typeof fetch>()
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
const listing = (trades: Trade[]) => ({ trades, total: trades.length, page: 1, page_size: 20 })

function renderPage(path: string) {
  render(<MemoryRouter initialEntries={[path]}><AuthProvider><Routes>
    <Route path="/items/:id" element={<ItemDetailPage />} /><Route path="/my-trades" element={<MyTradesPage />} />
  </Routes></AuthProvider></MemoryRouter>)
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  vi.spyOn(window, 'confirm').mockReturnValue(true)
  fetchMock.mockImplementation(async url => {
    const path = new URL(String(url)).pathname
    if (path.endsWith('/auth/me')) return json(user)
    if (path.endsWith('/price-reference')) return json({ items: [], sample_count: 0, min_price_cents: null, max_price_cents: null })
    if (path === '/api/items/1') return json(item)
    if (path === '/api/trades/mine') return json(listing([initialTrade]))
    return json(initialTrade, 201)
  })
})
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); fetchMock.mockReset() })

it('购买备注通过真实 API Client 提交，并阻止重复点击', async () => {
  let finish!: (response: Response) => void
  const original = fetchMock.getMockImplementation()!
  fetchMock.mockImplementation((url, options) => String(url).endsWith('/trade-intents')
    ? new Promise<Response>(resolve => { finish = resolve }) : original(url, options))
  renderPage('/items/1')
  const button = await screen.findByRole('button', { name: '我想购买' })
  fireEvent.change(screen.getByLabelText('购买备注（选填）'), { target: { value: ' 周五交接 ' } })
  fireEvent.click(button); fireEvent.click(button)
  expect(screen.getByRole('button', { name: '正在提交…' })).toBeDisabled()
  const calls = fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/trade-intents'))
  expect(calls).toHaveLength(1)
  expect(calls[0][1]).toEqual(expect.objectContaining({ method: 'POST', credentials: 'include', body: JSON.stringify({ note: '周五交接' }) }))
  finish(json(initialTrade, 201))
  expect(await screen.findByText(/购买意向已提交/)).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: '我想购买' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('link', { name: '查看我的交易 →' }))
  expect(await screen.findByRole('heading', { name: '我的交易' })).toBeInTheDocument()
  expect(await screen.findByText('待卖家处理')).toBeInTheDocument()
  expect(screen.getByText('意向价格 ¥12.00')).toBeInTheDocument()
})

it('重复购买错误有明确提示，保留到我的交易的入口', async () => {
  const original = fetchMock.getMockImplementation()!
  fetchMock.mockImplementation((url, options) => String(url).endsWith('/trade-intents')
    ? Promise.resolve(json({ detail: '你已有有效购买申请，请到我的交易查看。' }, 409)) : original(url, options))
  renderPage('/items/1')
  fireEvent.click(await screen.findByRole('button', { name: '我想购买' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('你已有有效购买申请')
  expect(screen.getByRole('button', { name: '我想购买' })).toBeEnabled()
  expect(screen.getAllByRole('link', { name: '我的交易' }).length).toBeGreaterThan(0)
})

it('卖出视图能接受和拒绝申请，并刷新状态', async () => {
  let trades = [7, 8].map(id => ({ ...initialTrade, id, seller_id: 2, buyer_id: 3, buyer: { id: 3, nickname: '买家同学' }, seller: { id: 2, nickname: '当前同学' } }))
  fetchMock.mockImplementation(async url => {
    const parsed = new URL(String(url))
    if (parsed.pathname.endsWith('/auth/me')) return json(user)
    if (parsed.pathname === '/api/trades/mine') return json(listing(parsed.searchParams.get('role') === 'seller' ? trades : []))
    const match = parsed.pathname.match(/\/trades\/(\d+)\/(accept|reject)/)
    if (match) {
      const id = Number(match[1]); trades = trades.map(trade => trade.id === id ? { ...trade, status: match[2] === 'accept' ? 'reserved' : 'rejected' } : trade)
      return json(trades.find(trade => trade.id === id))
    }
    return json({})
  })
  renderPage('/my-trades')
  fireEvent.click(screen.getByRole('button', { name: '我卖出的' }))
  const first = await screen.findByRole('article', { name: '交易 7' })
  expect(within(first).getByText('买家：买家同学')).toBeInTheDocument()
  fireEvent.click(within(first).getByRole('button', { name: '接受申请' }))
  await waitFor(() => expect(within(screen.getByRole('article', { name: '交易 7' })).getByText('已预留')).toBeInTheDocument())
  expect(screen.getByText(/已预留，可联系对方协商线下付款和交付/)).toBeInTheDocument()
  fireEvent.click(within(screen.getByRole('article', { name: '交易 8' })).getByRole('button', { name: '拒绝申请' }))
  await waitFor(() => expect(within(screen.getByRole('article', { name: '交易 8' })).getByText('已拒绝')).toBeInTheDocument())
})

it('单方确认显示等待，隐藏取消；刷新后显示双方成交时间', async () => {
  let trade: Trade = { ...initialTrade, status: 'reserved' }
  fetchMock.mockImplementation(async url => {
    const path = new URL(String(url)).pathname
    if (path.endsWith('/auth/me')) return json(user)
    if (path.endsWith('/confirm')) { trade = { ...trade, buyer_confirmed_at: timestamp }; return json(trade) }
    return json(listing([trade]))
  })
  renderPage('/my-trades')
  fireEvent.click(await screen.findByRole('button', { name: '确认交易完成' }))
  expect(await screen.findByText('你的成交确认已记录，等待对方确认。')).toBeInTheDocument()
  await waitFor(() => expect(screen.getByText('买方：已确认 · 卖方：未确认')).toBeInTheDocument())
  expect(screen.queryByRole('button', { name: '取消预留' })).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: '确认交易完成' })).not.toBeInTheDocument()
  trade = { ...trade, status: 'completed', seller_confirmed_at: timestamp, completed_at: timestamp }
  fireEvent.click(screen.getByRole('button', { name: '我卖出的' }))
  fireEvent.click(screen.getByRole('button', { name: '我买入的' }))
  expect(await screen.findByText('已成交')).toBeInTheDocument()
  expect(screen.getByText(/成交时间：/)).toBeInTheDocument()
})

it('已售出详情不再提供购买按钮', async () => {
  const original = fetchMock.getMockImplementation()!
  fetchMock.mockImplementation((url, options) => String(url).endsWith('/items/1') ? Promise.resolve(json({ ...item, availability: 'sold' })) : original(url, options))
  renderPage('/items/1')
  expect(await screen.findByText('已售出')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: '我想购买' })).not.toBeInTheDocument()
})
