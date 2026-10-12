import { apiClient } from './client'
import { env } from '../config/env'

export const CAMPUSES = ['五山校区', '大学城校区', '广州国际校区'] as const
export const CATEGORIES = ['教材资料', '数码配件', '生活用品', '运动户外', '兴趣娱乐', '其他'] as const
export const INTEREST_TAGS = ['摄影', '阅读', '数码', '运动', '音乐', '桌游', '学习', '其他'] as const
export type Campus = typeof CAMPUSES[number]
export type Category = typeof CATEGORIES[number]
export type InterestTag = typeof INTEREST_TAGS[number]
export type ItemMode = 'sale' | 'borrow' | 'gift'

export interface ItemImage { id: number; url: string; content_type: string }
export interface ItemOwner { id: number; nickname: string }
export interface Item {
  id: number; owner_id: number; title: string; description: string; category: Category; mode: ItemMode
  campus: Campus; price_cents: number | null; borrow_note: string | null; status: 'published' | 'withdrawn'
  availability: 'available' | 'reserved' | 'sold' | 'gifted' | 'borrowed' | 'return_pending' | 'unavailable'
  interest_tags: string[]; images: ItemImage[]; owner: ItemOwner; created_at: string; updated_at: string
}
export interface ItemList { items: Item[]; total: number; page: number; page_size: number }
export interface ItemInput {
  title: string; description: string; category: Category; mode: ItemMode; campus: Campus
  price_cents?: number | null; borrow_note?: string | null; interest_tags: InterestTag[]
}

export function imageUrl(path: string): string {
  return path.startsWith("http") ? path : `${env.apiBaseUrl}${path.replace(/^\/api/, '')}`
}

function parseItem(data: unknown): Item {
  if (typeof data !== 'object' || data === null || !('id' in data) || typeof data.id !== 'number' || !('title' in data) || typeof data.title !== 'string') throw new Error('Invalid item response')
  return data as Item
}
function parseList(data: unknown): ItemList {
  if (typeof data !== 'object' || data === null || !('items' in data) || !Array.isArray(data.items)) throw new Error('Invalid item list response')
  return { ...(data as ItemList), items: data.items.map(parseItem) }
}

export const itemsApi = {
  list: async (params: Record<string, string | number | undefined>, signal?: AbortSignal) => {
    const query = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => { if (value !== undefined && value !== '') query.set(key, String(value)) })
    return parseList(await apiClient.get(`/items${query.size ? `?${query}` : ''}`, signal))
  },
  mine: async (signal?: AbortSignal) => parseList(await apiClient.get('/items/mine', signal)),
  get: async (id: number, signal?: AbortSignal) => parseItem(await apiClient.get(`/items/${id}`, signal)),
  create: async (input: ItemInput) => parseItem(await apiClient.post('/items', input)),
  update: async (id: number, input: Partial<ItemInput>) => parseItem(await apiClient.patch(`/items/${id}`, input)),
  withdraw: async (id: number) => parseItem(await apiClient.delete(`/items/${id}`)),
  upload: async (id: number, file: File) => { const form = new FormData(); form.append('file', file); return parseItem(await apiClient.post(`/items/${id}/images`, form)) },
  removeImage: async (id: number, imageId: number) => parseItem(await apiClient.delete(`/items/${id}/images/${imageId}`)),
}
