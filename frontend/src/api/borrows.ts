import { apiClient } from './client'
import type { ItemImage, ItemOwner } from './items'

export type BorrowStatus = 'pending' | 'approved' | 'borrowed' | 'return_pending' | 'completed' | 'rejected' | 'canceled'
export type BorrowRole = 'borrower' | 'owner'
export type BorrowAction = 'approve' | 'reject' | 'cancel' | 'confirm-handover' | 'confirm-return'
export interface BorrowInput { requested_start_at: string; expected_return_at: string; note: string | null }
export interface Borrow {
  id: number; item_id: number; owner_id: number; borrower_id: number; requested_start_at: string; expected_return_at: string
  note: string | null; status: BorrowStatus; owner_handover_confirmed_at: string | null; borrower_handover_confirmed_at: string | null
  owner_return_confirmed_at: string | null; borrower_return_confirmed_at: string | null
  created_at: string; updated_at: string; borrowed_at: string | null; completed_at: string | null
  item: { id: number; title: string; images: ItemImage[] }; owner: ItemOwner; borrower: ItemOwner
}
export interface BorrowList { borrows: Borrow[]; total: number; page: number; page_size: number }
export const BORROW_STATUS_LABELS: Record<BorrowStatus, string> = {
  pending: '待物主处理', approved: '待交接', borrowed: '借用中', return_pending: '待双方确认归还', completed: '已归还', rejected: '已拒绝', canceled: '已取消',
}

function parseBorrow(data: unknown): Borrow {
  if (typeof data !== 'object' || data === null || !('id' in data) || typeof data.id !== 'number' || !('status' in data) || !(String(data.status) in BORROW_STATUS_LABELS)) throw new Error('Invalid borrow response')
  return data as Borrow
}

export const borrowsApi = {
  create: async (itemId: number, input: BorrowInput) => parseBorrow(await apiClient.post(`/items/${itemId}/borrow-requests`, input)),
  mine: async (role: BorrowRole, page = 1, signal?: AbortSignal): Promise<BorrowList> => {
    const data = await apiClient.get(`/borrows/mine?role=${role}&page=${page}&page_size=20`, signal)
    if (typeof data !== 'object' || data === null || !('borrows' in data) || !Array.isArray(data.borrows)) throw new Error('Invalid borrow list response')
    return { ...(data as BorrowList), borrows: data.borrows.map(parseBorrow) }
  },
  action: async (id: number, action: BorrowAction) => parseBorrow(await apiClient.post(`/borrows/${id}/${action}`)),
}
