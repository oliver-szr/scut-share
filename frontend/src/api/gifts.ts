import { apiClient } from './client'
import type { ItemImage, ItemOwner } from './items'

export interface Gift {
  id: number; item_id: number; owner_id: number; recipient_id: number; note: string | null
  status: 'pending' | 'approved' | 'rejected' | 'canceled' | 'completed'
  owner_confirmed_at: string | null; recipient_confirmed_at: string | null; completed_at: string | null
  created_at: string; updated_at: string; item: { id: number; title: string; images: ItemImage[] }; owner: ItemOwner; recipient: ItemOwner
}
export interface GiftList { gifts: Gift[]; total: number; page: number; page_size: number }
export type GiftAction = 'approve' | 'reject' | 'cancel' | 'confirm'
export const GIFT_STATUS = { pending: '待物主处理', approved: '已同意，待交接', rejected: '已拒绝', canceled: '已取消', completed: '转赠完成' }
export const giftsApi = {
  create: async (id: number, note: string) => await apiClient.post(`/items/${id}/gift-requests`, { note: note.trim() || null }) as Gift,
  mine: async (role: 'owner' | 'recipient', page: number, signal?: AbortSignal) => await apiClient.get(`/gifts/mine?role=${role}&page=${page}&page_size=20`, signal) as GiftList,
  action: async (id: number, action: GiftAction) => await apiClient.post(`/gifts/${id}/${action}`) as Gift,
}
