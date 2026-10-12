import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { AuthProvider } from './auth/AuthContext'
import { conversationsApi } from './api/conversations'
import type { Conversation, Message } from './api/conversations'
import type { Borrow } from './api/borrows'
import type { Item } from './api/items'
import { ItemDetailPage } from './pages/ItemDetailPage'
import { MessagesPage } from './pages/MessagesPage'
import { MyBorrowsPage } from './pages/MyBorrowsPage'

const timestamp = '2026-10-12T00:00:00Z'
const user = { id: 2, nickname: '当前同学', campus: '五山校区', student_no_masked: '***002', created_at: timestamp }
const conversation: Conversation = {
  id: 1, context_type: 'sale_item', item_id: 1, borrow_request_id: null, other_user: { id: 1, nickname: '卖家同学' },
  item: { id: 1, title: '课程相机', images: [] }, last_message: null, last_message_at: null, created_at: timestamp, updated_at: timestamp,
}
const second: Conversation = { ...conversation, id: 2, item_id: 2, other_user: { id: 3, nickname: '物主同学' }, item: { id: 2, title: '共享教材', images: [] } }
const message: Message = { id: 10, conversation_id: 1, sender_id: 1, content: '相机还在', created_at: timestamp }
const item: Item = {
  id: 1, owner_id: 1, title: '课程相机', description: '课程使用', mode: 'sale', category: '数码配件', campus: '五山校区',
  price_cents: 1200, borrow_note: null, status: 'published', availability: 'available', interest_tags: [], images: [],
  owner: { id: 1, nickname: '卖家同学' }, created_at: timestamp, updated_at: timestamp,
}
const json = (data: unknown) => new Response(JSON.stringify(data), { headers: { 'Content-Type': 'application/json' } })
const fetchMock = vi.fn<typeof fetch>()

function renderPage(path = '/messages') {
  return render(<MemoryRouter initialEntries={[path]}><AuthProvider><Routes>
    <Route path="/messages" element={<MessagesPage />} />
    <Route path="/items/:id" element={<ItemDetailPage />} />
    <Route path="/my-borrows" element={<MyBorrowsPage />} />
  </Routes></AuthProvider></MemoryRouter>)
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  fetchMock.mockImplementation(async url => json(String(url).includes('/price-reference') ? { items: [], sample_count: 0, min_price_cents: null, max_price_cents: null } : String(url).includes('/auth/me') ? user : item))
  vi.spyOn(document, 'hidden', 'get').mockReturnValue(false)
  vi.spyOn(conversationsApi, 'list').mockResolvedValue({ conversations: [conversation, second], total: 2, page: 1, page_size: 20 })
  vi.spyOn(conversationsApi, 'get').mockImplementation(async id => id === 1 ? conversation : second)
  vi.spyOn(conversationsApi, 'messages').mockImplementation(async id => ({ messages: id === 1 ? [message] : [], has_more: false }))
  vi.spyOn(conversationsApi, 'send').mockImplementation(async (id, content) => ({ ...message, id: 12, conversation_id: id, sender_id: user.id, content }))
})
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); fetchMock.mockReset() })

it('会话列表展示商品和对方，切换会话只显示对应历史，手机返回列表', async () => {
  renderPage()
  fireEvent.click(await screen.findByRole('button', { name: /卖家同学.*课程相机/ }))
  expect(await screen.findByText('相机还在')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /物主同学.*共享教材/ }))
  expect(await screen.findByText('还没有消息，发送第一句话吧。')).toBeInTheDocument()
  expect(screen.queryByText('相机还在')).not.toBeInTheDocument()
  expect(conversationsApi.messages).toHaveBeenCalledWith(2, {}, expect.any(AbortSignal))
  fireEvent.click(screen.getByRole('button', { name: '← 返回会话列表' }))
  expect(screen.getByText('选择一个会话开始沟通')).toBeInTheDocument()
})

it('发送文本即刻展示，防重复点击，HTML 仅按文本显示，轮询去重且不跳过未读回复', async () => {
  let finish!: (value: Message) => void
  vi.mocked(conversationsApi.send).mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
  vi.useFakeTimers()
  await act(async () => { renderPage('/messages?conversation=1') })
  expect(screen.getByText('相机还在')).toBeInTheDocument()
  const text = "<script>alert('普通文本')</script>"
  fireEvent.change(screen.getByLabelText('消息内容'), { target: { value: ` ${text} ` } })
  fireEvent.click(screen.getByRole('button', { name: '发送' }))
  fireEvent.click(screen.getByRole('button', { name: '正在发送…' }))
  expect(conversationsApi.send).toHaveBeenCalledTimes(1)
  expect(conversationsApi.send).toHaveBeenCalledWith(1, text, expect.any(AbortSignal))
  await act(async () => finish({ ...message, id: 12, sender_id: 2, content: text }))
  expect(within(screen.getByLabelText('历史消息')).getByText(text)).toBeInTheDocument()
  expect(screen.getByLabelText('历史消息').querySelector('script')).toBeNull()
  const reply = { ...message, id: 11, content: '可以在教学楼交付' }
  vi.mocked(conversationsApi.messages).mockResolvedValueOnce({ messages: [reply, { ...message, id: 12, sender_id: 2, content: text }], has_more: false })
  await act(async () => { await vi.advanceTimersByTimeAsync(8000) })
  expect(conversationsApi.messages).toHaveBeenLastCalledWith(1, { after_id: 10 }, expect.any(AbortSignal))
  expect(screen.getByText(reply.content)).toBeInTheDocument()
  expect(screen.getAllByLabelText('消息 12')).toHaveLength(1)
})

it('网络异常暂停轮询，保留重载入口，隐藏页面及退出聊天停止轮询', async () => {
  vi.useFakeTimers()
  const view = renderPage('/messages?conversation=1')
  await act(async () => {})
  expect(screen.getByText('相机还在')).toBeInTheDocument()
  vi.mocked(conversationsApi.messages).mockRejectedValueOnce(new Error('network'))
  await act(async () => { await vi.advanceTimersByTimeAsync(8000) })
  expect(screen.getByRole('alert')).toHaveTextContent('自动更新已暂停')
  const calls = vi.mocked(conversationsApi.messages).mock.calls.length
  await act(async () => { await vi.advanceTimersByTimeAsync(24000) })
  expect(conversationsApi.messages).toHaveBeenCalledTimes(calls)
  fireEvent.change(screen.getByLabelText('消息内容'), { target: { value: '手动发送' } })
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: '发送' })) })
  expect(screen.getByRole('button', { name: '重新加载' })).toBeInTheDocument()
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: '重新加载' })) })
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  vi.spyOn(document, 'hidden', 'get').mockReturnValue(true)
  act(() => document.dispatchEvent(new Event('visibilitychange')))
  const hiddenCalls = vi.mocked(conversationsApi.messages).mock.calls.length
  await act(async () => { await vi.advanceTimersByTimeAsync(16000) })
  expect(conversationsApi.messages).toHaveBeenCalledTimes(hiddenCalls)
  vi.spyOn(document, 'hidden', 'get').mockReturnValue(false)
  act(() => document.dispatchEvent(new Event('visibilitychange')))
  await act(async () => { await vi.advanceTimersByTimeAsync(8000) })
  expect(conversationsApi.messages).toHaveBeenCalledTimes(hiddenCalls + 1)
  view.unmount()
  await act(async () => { await vi.advanceTimersByTimeAsync(16000) })
  expect(conversationsApi.messages).toHaveBeenCalledTimes(hiddenCalls + 1)
})

it('切换会话取消旧请求，旧结果不污染当前消息', async () => {
  let finish!: (value: { messages: Message[]; has_more: boolean }) => void
  vi.mocked(conversationsApi.messages).mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
  renderPage('/messages?conversation=1')
  const target = await screen.findByRole('button', { name: /物主同学.*共享教材/ })
  await waitFor(() => expect(conversationsApi.messages).toHaveBeenCalledTimes(1))
  const firstSignal = vi.mocked(conversationsApi.messages).mock.calls[0][2]!
  fireEvent.click(target)
  expect(await screen.findByText('还没有消息，发送第一句话吧。')).toBeInTheDocument()
  expect(firstSignal.aborted).toBe(true)
  await act(async () => finish({ messages: [message], has_more: false }))
  expect(screen.queryByText('相机还在')).not.toBeInTheDocument()
})

it('sale 商品联系卖家调用真实会话 API，再进入聊天', async () => {
  // Use the real API Client for the entry, including cookie credentials and an empty identity-free body.
  fetchMock.mockImplementation(async url => String(url).endsWith('/items/1/conversations')
    ? json(conversation) : json(String(url).includes('/price-reference') ? { items: [], sample_count: 0, min_price_cents: null, max_price_cents: null } : String(url).includes('/auth/me') ? user : item))
  renderPage('/items/1')
  fireEvent.click(await screen.findByRole('button', { name: '联系卖家' }))
  expect(await screen.findByText('相机还在')).toBeInTheDocument()
  const call = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/items/1/conversations'))!
  expect(call[1]).toEqual(expect.objectContaining({ method: 'POST', credentials: 'include', body: '{}' }))
})

it('借还记录只在同意及后续阶段展示联系入口，并使用申请 ID', async () => {
  const states: Borrow['status'][] = ['pending', 'rejected', 'approved', 'borrowed', 'return_pending', 'completed', 'canceled']
  const rows: Borrow[] = states.map((status, i) => ({
    id: i + 1, item_id: 1, owner_id: 1, borrower_id: 2, requested_start_at: timestamp, expected_return_at: '2030-01-03T00:00:00Z',
    note: null, status, owner_handover_confirmed_at: null, borrower_handover_confirmed_at: null,
    owner_return_confirmed_at: null, borrower_return_confirmed_at: null, borrowed_at: null, completed_at: null,
    created_at: timestamp, updated_at: timestamp, item: conversation.item, owner: conversation.other_user, borrower: { id: 2, nickname: '当前同学' },
  }))
  fetchMock.mockImplementation(async url => json(String(url).includes('/auth/me') ? user : { borrows: rows, total: 7, page: 1, page_size: 20 }))
  const start = vi.spyOn(conversationsApi, 'start').mockResolvedValue({ ...conversation, context_type: 'borrow_request', borrow_request_id: 3 })
  renderPage('/my-borrows')
  await screen.findByLabelText('借还 1')
  // Explicitly check both denied and allowed states without duplicating page tests.
  for (const row of rows) {
    const button = within(screen.getByLabelText(`借还 ${row.id}`)).queryByRole('button', { name: '联系对方' })
    if (['pending', 'rejected', 'canceled'].includes(row.status)) expect(button).not.toBeInTheDocument()
    else expect(button).toBeInTheDocument()
  }
  fireEvent.click(within(screen.getByLabelText('借还 3')).getByRole('button', { name: '联系对方' }))
  expect(await screen.findByText('相机还在')).toBeInTheDocument()
  expect(start).toHaveBeenCalledWith('borrow', 3)
})
