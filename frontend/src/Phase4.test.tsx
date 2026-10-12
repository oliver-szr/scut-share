import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { AuthProvider } from './auth/AuthContext'
import type { Item } from './api/items'
import type { Borrow } from './api/borrows'
import { ItemDetailPage } from './pages/ItemDetailPage'
import { MyBorrowsPage } from './pages/MyBorrowsPage'

const timestamp = '2026-10-12T00:00:00Z'
const user = { id: 2, nickname: '当前同学', campus: '五山校区', student_no_masked: '***002', created_at: timestamp }
const item: Item = {
  id: 1, owner_id: 1, title: '共享相机', description: '课程免费借用', mode: 'borrow', category: '数码配件', campus: '五山校区',
  price_cents: null, borrow_note: '请按时归还', status: 'published', availability: 'available', interest_tags: [], images: [],
  owner: { id: 1, nickname: '物主同学' }, created_at: timestamp, updated_at: timestamp,
}
const initialBorrow: Borrow = {
  id: 7, item_id: 1, owner_id: 1, borrower_id: 2, requested_start_at: '2030-01-01T00:00:00Z', expected_return_at: '2030-01-03T00:00:00Z',
  note: '课程使用', status: 'pending', owner_handover_confirmed_at: null, borrower_handover_confirmed_at: null,
  owner_return_confirmed_at: null, borrower_return_confirmed_at: null, borrowed_at: null, completed_at: null,
  created_at: timestamp, updated_at: timestamp, item: { id: 1, title: '共享相机', images: [] },
  owner: { id: 1, nickname: '物主同学' }, borrower: { id: 2, nickname: '当前同学' },
}
const fetchMock = vi.fn<typeof fetch>()
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
const listing = (borrows: Borrow[]) => ({ borrows, total: borrows.length, page: 1, page_size: 20 })

function renderPage(path: string) {
  render(<MemoryRouter initialEntries={[path]}><AuthProvider><Routes>
    <Route path="/items/:id" element={<ItemDetailPage />} /><Route path="/my-borrows" element={<MyBorrowsPage />} />
  </Routes></AuthProvider></MemoryRouter>)
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  vi.spyOn(window, 'confirm').mockReturnValue(true)
  fetchMock.mockImplementation(async url => {
    const path = new URL(String(url)).pathname
    if (path.endsWith('/auth/me')) return json(user)
    if (path === '/api/items/1') return json(item)
    if (path === '/api/borrows/mine') return json(listing([initialBorrow]))
    return json(initialBorrow, 201)
  })
})
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); fetchMock.mockReset() })

it('详情打开免费申请表单，以 UTC 提交时间和备注并防重复点击', async () => {
  let finish!: (response: Response) => void
  const original = fetchMock.getMockImplementation()!
  fetchMock.mockImplementation((url, options) => String(url).endsWith('/borrow-requests')
    ? new Promise<Response>(resolve => { finish = resolve }) : original(url, options))
  renderPage('/items/1')
  fireEvent.click(await screen.findByRole('button', { name: '申请免费借用' }))
  fireEvent.change(screen.getByLabelText('预计开始时间'), { target: { value: '2030-01-01T10:00' } })
  fireEvent.change(screen.getByLabelText('预计归还时间'), { target: { value: '2030-01-03T10:00' } })
  fireEvent.change(screen.getByLabelText('申请备注（选填）'), { target: { value: ' 课程使用 ' } })
  const button = screen.getByRole('button', { name: '提交借用申请' })
  fireEvent.click(button); fireEvent.click(button)
  expect(screen.getByRole('button', { name: '正在提交…' })).toBeDisabled()
  const calls = fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/borrow-requests'))
  expect(calls).toHaveLength(1)
  expect(calls[0][1]).toEqual(expect.objectContaining({ method: 'POST', credentials: 'include', body: JSON.stringify({
    requested_start_at: new Date('2030-01-01T10:00').toISOString(), expected_return_at: new Date('2030-01-03T10:00').toISOString(), note: '课程使用',
  }) }))
  expect(screen.queryByLabelText(/租金|押金|手续费/)).not.toBeInTheDocument()
  finish(json(initialBorrow, 201))
  expect(await screen.findByText(/借用申请已提交/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('link', { name: '查看我的借还 →' }))
  expect(await screen.findByText('待物主处理')).toBeInTheDocument()
  expect(screen.getByText('物主：物主同学')).toBeInTheDocument()
})

it('表单阻止逆序时间，重复有效申请错误保留填写内容', async () => {
  const original = fetchMock.getMockImplementation()!
  fetchMock.mockImplementation((url, options) => String(url).endsWith('/borrow-requests')
    ? Promise.resolve(json({ detail: '你已有未结束的借用申请，请到我的借还查看。' }, 409)) : original(url, options))
  renderPage('/items/1')
  fireEvent.click(await screen.findByRole('button', { name: '申请免费借用' }))
  fireEvent.change(screen.getByLabelText('预计开始时间'), { target: { value: '2030-01-03T10:00' } })
  fireEvent.change(screen.getByLabelText('预计归还时间'), { target: { value: '2030-01-01T10:00' } })
  const form = screen.getByRole('button', { name: '提交借用申请' }).closest('form')!
  fireEvent.submit(form)
  expect(await screen.findByRole('alert')).toHaveTextContent('预计归还时间必须晚于预计开始时间')
  expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/borrow-requests'))).toHaveLength(0)
  fireEvent.change(screen.getByLabelText('预计归还时间'), { target: { value: '2030-01-05T10:00' } })
  fireEvent.submit(form)
  expect(await screen.findByRole('alert')).toHaveTextContent('你已有未结束的借用申请')
  expect(screen.getByLabelText('预计开始时间')).toHaveValue('2030-01-03T10:00')
  expect(screen.getByRole('button', { name: '提交借用申请' })).toBeEnabled()
})

it('借出列表允许物主同意、拒绝并确认已交出，单方交接仍待确认', async () => {
  let borrows: Borrow[] = [
    { ...initialBorrow, owner_id: 2, borrower_id: 3, owner: { id: 2, nickname: '当前同学' }, borrower: { id: 3, nickname: '借用同学' } },
    { ...initialBorrow, id: 8, item_id: 2, item: { id: 2, title: '共享教材', images: [] }, owner_id: 2, borrower_id: 3, owner: { id: 2, nickname: '当前同学' }, borrower: { id: 3, nickname: '借用同学' } },
  ]
  fetchMock.mockImplementation(async url => {
    const parsed = new URL(String(url))
    if (parsed.pathname.endsWith('/auth/me')) return json(user)
    if (parsed.pathname === '/api/borrows/mine') return json(listing(parsed.searchParams.get('role') === 'owner' ? borrows : []))
    const match = parsed.pathname.match(/\/borrows\/(\d+)\/(approve|reject|confirm-handover)/)
    if (match) {
      borrows = borrows.map(borrow => borrow.id !== Number(match[1]) ? borrow : match[2] === 'confirm-handover'
        ? { ...borrow, owner_handover_confirmed_at: timestamp } : { ...borrow, status: match[2] === 'approve' ? 'approved' : 'rejected' })
      return json(borrows.find(borrow => borrow.id === Number(match[1])))
    }
    return json({})
  })
  renderPage('/my-borrows')
  fireEvent.click(screen.getByRole('button', { name: '我借出的' }))
  const first = await screen.findByRole('article', { name: '借还 7' })
  expect(within(first).getByText('借用人：借用同学')).toBeInTheDocument()
  fireEvent.click(within(first).getByRole('button', { name: '同意申请' }))
  fireEvent.click(await screen.findByRole('button', { name: '确认已交出物品' }))
  await waitFor(() => expect(screen.getByText('借出确认 · 物主：已确认 · 借用人：未确认')).toBeInTheDocument())
  expect(screen.getByText('待交接')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: '取消待交接' })).not.toBeInTheDocument()
  fireEvent.click(within(screen.getByRole('article', { name: '借还 8' })).getByRole('button', { name: '拒绝申请' }))
  expect(await screen.findByText('已拒绝')).toBeInTheDocument()
})

it('借用人交接与归还确认各等待另一方，逾期不改变状态，归还后保留历史', async () => {
  let borrow: Borrow = { ...initialBorrow, status: 'approved', requested_start_at: '2020-01-01T00:00:00Z', expected_return_at: '2020-01-03T00:00:00Z' }
  fetchMock.mockImplementation(async url => {
    const path = new URL(String(url)).pathname
    if (path.endsWith('/auth/me')) return json(user)
    if (path.endsWith('/confirm-handover')) { borrow = { ...borrow, borrower_handover_confirmed_at: timestamp }; return json(borrow) }
    if (path.endsWith('/confirm-return')) { borrow = { ...borrow, borrower_return_confirmed_at: timestamp, status: 'return_pending' }; return json(borrow) }
    return json(listing([borrow]))
  })
  renderPage('/my-borrows')
  fireEvent.click(await screen.findByRole('button', { name: '确认已收到物品' }))
  expect(await screen.findByText('你的交接确认已记录，等待对方确认。')).toBeInTheDocument()
  await screen.findByText('借出确认 · 物主：未确认 · 借用人：已确认')
  expect(screen.queryByRole('button', { name: '确认已归还物品' })).not.toBeInTheDocument()
  borrow = { ...borrow, owner_handover_confirmed_at: timestamp, borrowed_at: timestamp, status: 'borrowed' }
  fireEvent.click(screen.getByRole('button', { name: '刷新借还' }))
  const returnButton = await screen.findByRole('button', { name: '确认已归还物品' })
  expect(screen.getByText('已逾期')).toBeInTheDocument()
  expect(screen.getByText('借用中')).toBeInTheDocument()
  fireEvent.click(returnButton)
  expect(await screen.findByText('你的归还确认已记录，等待对方确认。')).toBeInTheDocument()
  await screen.findByText('待双方确认归还')
  expect(screen.queryByRole('button', { name: '确认已归还物品' })).not.toBeInTheDocument()
  borrow = { ...borrow, owner_return_confirmed_at: timestamp, completed_at: timestamp, status: 'completed' }
  fireEvent.click(screen.getByRole('button', { name: '刷新借还' }))
  expect(await screen.findByText('已归还')).toBeInTheDocument()
  expect(screen.getByText(/归还完成：/)).toBeInTheDocument()
  expect(screen.queryByText('已逾期')).not.toBeInTheDocument()
})

it('物主可以确认收到归还物品并展示双方完成反馈', async () => {
  let borrow: Borrow = { ...initialBorrow, owner_id: 2, borrower_id: 3, owner: { id: 2, nickname: '当前同学' }, borrower: { id: 3, nickname: '借用同学' }, status: 'return_pending',
    owner_handover_confirmed_at: timestamp, borrower_handover_confirmed_at: timestamp, borrowed_at: timestamp, borrower_return_confirmed_at: timestamp }
  fetchMock.mockImplementation(async url => {
    const parsed = new URL(String(url))
    if (parsed.pathname.endsWith('/auth/me')) return json(user)
    if (parsed.pathname.endsWith('/confirm-return')) { borrow = { ...borrow, owner_return_confirmed_at: timestamp, completed_at: timestamp, status: 'completed' }; return json(borrow) }
    return json(listing(parsed.searchParams.get('role') === 'owner' ? [borrow] : []))
  })
  renderPage('/my-borrows')
  fireEvent.click(screen.getByRole('button', { name: '我借出的' }))
  fireEvent.click(await screen.findByRole('button', { name: '确认已收到归还物品' }))
  expect(await screen.findByText('双方已确认归还，物品重新可借，历史记录已保留。')).toBeInTheDocument()
  expect(await screen.findByText('已归还')).toBeInTheDocument()
})

it('借用中物品详情隐藏申请入口', async () => {
  const original = fetchMock.getMockImplementation()!
  fetchMock.mockImplementation((url, options) => String(url).endsWith('/items/1') ? Promise.resolve(json({ ...item, availability: 'borrowed' })) : original(url, options))
  renderPage('/items/1')
  expect(await screen.findByText('借用中')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: '申请免费借用' })).not.toBeInTheDocument()
})
