import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import type { ReactElement } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from './auth/AuthContext'
import { ApiError } from './api/client'
import { itemsApi } from './api/items'
import type { Item, ItemList } from './api/items'
import { ItemForm } from './components/ItemForm'
import { ItemDetailPage } from './pages/ItemDetailPage'
import { ItemsPage } from './pages/ItemsPage'
import { MyItemsPage } from './pages/MyItemsPage'
import { ItemFormPage } from './pages/ItemFormPage'

const fetchMock = vi.fn<typeof fetch>()
const currentUser = { id: 2, nickname: '浏览同学', campus: '五山校区' as const, created_at: '2026-10-12T00:00:00Z', student_no_masked: '********001' }
const item: Item = {
  id: 1, owner_id: 1, title: '测试相机', description: '可用于课程拍摄', category: '数码配件', mode: 'sale', campus: '五山校区',
  price_cents: 1200, borrow_note: null, status: 'published', availability: 'available', interest_tags: ['摄影', '数码'],
  images: [{ id: 7, url: '/api/items/images/camera.png', content_type: 'image/png' }], owner: { id: 1, nickname: '发布同学' },
  created_at: '2026-10-12T00:00:00Z', updated_at: '2026-10-12T00:00:00Z',
}

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
}

function listResponse(items: Item[] = [item]): ItemList {
  return { items, total: items.length, page: 1, page_size: 12 }
}

function renderWithAuth(element: ReactElement, path = '/') {
  return render(<MemoryRouter initialEntries={[path]}><AuthProvider>{element}</AuthProvider></MemoryRouter>)
}

function renderDetail() {
  return render(<MemoryRouter initialEntries={['/items/1']}><AuthProvider><Routes><Route path="/items/:id" element={<ItemDetailPage />} /></Routes></AuthProvider></MemoryRouter>)
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  fetchMock.mockImplementation(async url => {
    const path = new URL(String(url)).pathname
    if (path.endsWith('/auth/me')) return json(currentUser)
    if (path.endsWith('/price-reference')) return json({ items: [], sample_count: 0, min_price_cents: null, max_price_cents: null })
    if (path === '/api/items/mine') return json(listResponse([item]))
    if (path === '/api/items/1') return json(item)
    if (path === '/api/items') return json(listResponse())
    return json({ status: 'ok' })
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  fetchMock.mockReset()
})

describe('Phase 2 物品广场', () => {
  it('正常渲染物品列表、校区、价格和标签', async () => {
    renderWithAuth(<ItemsPage />)
    expect(await screen.findByRole('heading', { name: '物品广场' })).toBeInTheDocument()
    expect(await screen.findByText('测试相机')).toBeInTheDocument()
    expect(screen.getAllByText('五山校区').length).toBeGreaterThan(1)
    expect(screen.getByText('¥12.00')).toBeInTheDocument()
    expect(screen.getByText('摄影')).toBeInTheDocument()
  })

  it('空列表显示空状态', async () => {
    fetchMock.mockImplementation(async url => new URL(String(url)).pathname.endsWith('/auth/me') ? json(currentUser) : json(listResponse([])))
    renderWithAuth(<ItemsPage />)
    expect(await screen.findByRole('heading', { name: '还没有找到物品' })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /发布物品/ })).toHaveLength(2)
  })

  it('关键词和分类筛选会更新真实查询参数', async () => {
    renderWithAuth(<ItemsPage />)
    await screen.findByText('测试相机')
    fireEvent.change(screen.getByRole('textbox', { name: '关键词' }), { target: { value: '相机' } })
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('q=%E7%9B%B8%E6%9C%BA'))).toBe(true))
    fireEvent.change(screen.getByRole('combobox', { name: '分类' }), { target: { value: '教材资料' } })
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('category=%E6%95%99%E6%9D%90%E8%B5%84%E6%96%99'))).toBe(true))
  })

  it('首页模式链接会初始化模式筛选，失败后可以重试', async () => {
    let listingCalls = 0
    fetchMock.mockImplementation(async url => {
      const path = new URL(String(url)).pathname
      if (path.endsWith('/auth/me')) return json(currentUser)
      if (path === '/api/items') { listingCalls += 1; return listingCalls === 1 ? json({ detail: '暂时失败' }, 503) : json(listResponse([item])) }
      return json({ status: 'ok' })
    })
    renderWithAuth(<ItemsPage />, '/items?mode=borrow')
    expect(await screen.findByRole('alert')).toHaveTextContent('暂时失败')
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('mode=borrow'))).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: '重试' }))
    expect(await screen.findByText('测试相机')).toBeInTheDocument()
    expect(listingCalls).toBe(2)
  })
})

describe('Phase 2 发布表单', () => {
  function fillSaleForm() {
    fireEvent.change(screen.getByLabelText('物品名称'), { target: { value: '课程相机' } })
    fireEvent.change(screen.getByLabelText('物品描述'), { target: { value: '成色良好' } })
    fireEvent.change(screen.getByLabelText('售价（元）'), { target: { value: '12' } })
  }

  it('可以切换出售和免费借还，借还模式不显示租金', () => {
    render(<ItemForm onSuccess={vi.fn()} />)
    expect(screen.getByLabelText('售价（元）')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '免费借还' }))
    expect(screen.queryByLabelText('售价（元）')).not.toBeInTheDocument()
    expect(screen.getByLabelText('借用说明')).toBeInTheDocument()
  })

  it('出售模式缺少合法价格时阻止提交', async () => {
    const create = vi.spyOn(itemsApi, 'create')
    const invalidPriceRender = render(<ItemForm onSuccess={vi.fn()} />)
    fireEvent.change(screen.getByLabelText('物品名称'), { target: { value: '课程相机' } })
    fireEvent.change(screen.getByLabelText('物品描述'), { target: { value: '成色良好' } })
    fireEvent.change(screen.getByLabelText('售价（元）'), { target: { value: '0' } })
    fireEvent.submit(screen.getByRole('button', { name: '发布物品' }).closest('form')!)
    expect(await screen.findByRole('alert')).toHaveTextContent('大于 0 的售价')
    expect(create).not.toHaveBeenCalled()
    invalidPriceRender.unmount()
  })

  it('发布 API 失败和图片上传失败会显示错误', async () => {
    vi.spyOn(itemsApi, 'create').mockRejectedValueOnce(new ApiError(503, '服务暂时不可用'))
    const failedCreateRender = render(<ItemForm onSuccess={vi.fn()} />)
    fillSaleForm()
    fireEvent.submit(screen.getByRole('button', { name: '发布物品' }).closest('form')!)
    expect(await screen.findByRole('alert')).toHaveTextContent('服务暂时不可用')

    failedCreateRender.unmount()
    vi.restoreAllMocks()
    const created = vi.spyOn(itemsApi, 'create').mockResolvedValue(item)
    vi.spyOn(itemsApi, 'upload').mockRejectedValue(new ApiError(415, '图片格式不支持'))
    const { unmount } = render(<ItemForm onSuccess={vi.fn()} />)
    fillSaleForm()
    const file = new File(['image'], 'camera.png', { type: 'image/png' })
    fireEvent.change(screen.getByLabelText(/图片（最多 3 张/), { target: { files: [file] } })
    fireEvent.submit(screen.getByRole('button', { name: '发布物品' }).closest('form')!)
    expect(await screen.findByRole('alert')).toHaveTextContent('图片格式不支持')
    expect(created).toHaveBeenCalled()
    unmount()
  })
})

describe('Phase 2 详情和我的发布', () => {
  it('详情展示图片、描述、标签，非物主看不到编辑和下架操作', async () => {
    renderDetail()
    expect(await screen.findByRole('heading', { name: '测试相机' })).toBeInTheDocument()
    expect(screen.getByAltText('测试相机')).toHaveAttribute('src', 'http://127.0.0.1:8000/api/items/images/camera.png')
    expect(screen.getByText('可用于课程拍摄')).toBeInTheDocument()
    expect(screen.getByText('摄影')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('link', { name: '个人中心' })).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: '编辑' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '下架' })).not.toBeInTheDocument()
  })

  it('我的发布页面显示物品和状态', async () => {
    renderWithAuth(<MyItemsPage />)
    expect(await screen.findByRole('heading', { name: '我的发布' })).toBeInTheDocument()
    expect(await screen.findByText('测试相机')).toBeInTheDocument()
    expect(screen.getByText('已发布')).toBeInTheDocument()
  })

  it('我的发布能编辑已下架物品，不请求公开详情', async () => {
    const withdrawn = { ...item, owner_id: currentUser.id, status: 'withdrawn' as const }
    vi.spyOn(itemsApi, 'mine').mockResolvedValue(listResponse([withdrawn]))
    const update = vi.spyOn(itemsApi, 'update').mockResolvedValue({ ...withdrawn, title: '下架后更新' })
    renderWithAuth(<MyItemsPage />)
    expect(await screen.findByText('已下架')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '编辑已下架物品' }))
    fireEvent.change(screen.getByLabelText('物品名称'), { target: { value: '下架后更新' } })
    fireEvent.submit(screen.getByRole('button', { name: '保存修改' }).closest('form')!)
    expect(await screen.findByText('下架后更新')).toBeInTheDocument()
    expect(update).toHaveBeenCalledWith(item.id, expect.objectContaining({ title: '下架后更新' }))
    expect(fetchMock.mock.calls.some(([url]) => new URL(String(url)).pathname === '/api/items/1')).toBe(false)
  })
})

describe('Phase 2 发布回归', () => {
  function fillForm() {
    fireEvent.change(screen.getByLabelText('物品名称'), { target: { value: '课程相机' } })
    fireEvent.change(screen.getByLabelText('物品描述'), { target: { value: '成色良好' } })
    fireEvent.change(screen.getByLabelText('售价（元）'), { target: { value: '12' } })
  }

  it('发布成功跳转到详情', async () => {
    vi.spyOn(itemsApi, 'create').mockResolvedValue(item)
    render(<MemoryRouter initialEntries={['/items/new']}><AuthProvider><Routes><Route path="/items/new" element={<ItemFormPage />} /><Route path="/items/:id" element={<h1>发布完成详情</h1>} /></Routes></AuthProvider></MemoryRouter>)
    fillForm()
    fireEvent.submit(screen.getByRole('button', { name: '发布物品' }).closest('form')!)
    expect(await screen.findByRole('heading', { name: '发布完成详情' })).toBeInTheDocument()
  })

  it('选择超过三张图片时阻止发布', async () => {
    const create = vi.spyOn(itemsApi, 'create')
    render(<ItemForm onSuccess={vi.fn()} />)
    fillForm()
    const files = Array.from({ length: 4 }, (_, index) => new File(['image'], `${index}.png`, { type: 'image/png' }))
    fireEvent.change(screen.getByLabelText(/图片（最多 3 张/), { target: { files } })
    fireEvent.submit(screen.getByRole('button', { name: '发布物品' }).closest('form')!)
    expect(await screen.findByRole('alert')).toHaveTextContent('最多选择 3 张图片')
    expect(create).not.toHaveBeenCalled()
  })

  it('部分图片上传失败后重试不会重复创建物品或上传成功的文件', async () => {
    const create = vi.spyOn(itemsApi, 'create').mockResolvedValue(item)
    vi.spyOn(itemsApi, 'update').mockResolvedValue(item)
    const upload = vi.spyOn(itemsApi, 'upload').mockResolvedValueOnce(item).mockRejectedValueOnce(new ApiError(503, '上传暂时失败')).mockResolvedValueOnce(item)
    const success = vi.fn()
    render(<ItemForm onSuccess={success} />)
    fillForm()
    const files = [new File(['a'], 'a.png', { type: 'image/png' }), new File(['b'], 'b.png', { type: 'image/png' })]
    fireEvent.change(screen.getByLabelText(/图片（最多 3 张/), { target: { files } })
    fireEvent.submit(screen.getByRole('button', { name: '发布物品' }).closest('form')!)
    expect(await screen.findByRole('alert')).toHaveTextContent('上传暂时失败')
    expect(screen.getByLabelText('物品名称')).toHaveValue('课程相机')
    expect(success).not.toHaveBeenCalled()
    fireEvent.submit(screen.getByRole('button', { name: '发布物品' }).closest('form')!)
    await waitFor(() => expect(success).toHaveBeenCalledWith(item))
    expect(create).toHaveBeenCalledTimes(1)
    expect(upload.mock.calls.map(([, file]) => file)).toEqual([files[0], files[1], files[1]])
  })
})
