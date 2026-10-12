import { apiClient } from './client'
import type { ItemImage, ItemOwner } from './items'

export type TradeStatus = 'pending' | 'reserved' | 'rejected' | 'canceled' | 'completed'
export type TradeRole = 'buyer' | 'seller'
export type TradeAction = 'accept' | 'reject' | 'cancel' | 'confirm'
export interface Trade {
  id: number; item_id: number; buyer_id: number; seller_id: number; price_cents_snapshot: number
  note: string | null; status: TradeStatus; buyer_confirmed_at: string | null; seller_confirmed_at: string | null
  created_at: string; updated_at: string; completed_at: string | null
  item: { id: number; title: string; images: ItemImage[] }; buyer: ItemOwner; seller: ItemOwner
}
export interface TradeList { trades: Trade[]; total: number; page: number; page_size: number }
export const TRADE_STATUS_LABELS: Record<TradeStatus, string> = {
  pending: '待卖家处理', reserved: '已预留', rejected: '已拒绝', canceled: '已取消', completed: '已成交',
}

function parseTrade(data: unknown): Trade {
  if (typeof data !== 'object' || data === null || !('id' in data) || typeof data.id !== 'number' || !('status' in data) || !(String(data.status) in TRADE_STATUS_LABELS)) throw new Error('Invalid trade response')
  return data as Trade
}

export const tradesApi = {
  create: async (itemId: number, note: string) => parseTrade(await apiClient.post(`/items/${itemId}/trade-intents`, { note: note.trim() || null })),
  mine: async (role: TradeRole, page = 1, signal?: AbortSignal): Promise<TradeList> => {
    const data = await apiClient.get(`/trades/mine?role=${role}&page=${page}&page_size=20`, signal)
    if (typeof data !== 'object' || data === null || !('trades' in data) || !Array.isArray(data.trades)) throw new Error('Invalid trade list response')
    return { ...(data as TradeList), trades: data.trades.map(parseTrade) }
  },
  action: async (id: number, action: TradeAction) => parseTrade(await apiClient.post(`/trades/${id}/${action}`)),
}
