import { apiClient } from './client'

export type ReportTarget = 'item' | 'trade' | 'borrow' | 'message'
export type Resolution = 'handled' | 'dismissed'
export interface Report {
  id: number; target_type: ReportTarget; target_id: number; reason: string; description: string
  status: 'pending' | Resolution; resolution_note: string | null; created_at: string; resolved_at: string | null
  appeal: { id: number; reason: string; status: 'pending' | 'reviewed'; decision: Resolution | null; review_note: string | null; created_at: string; reviewed_at: string | null } | null
}
export interface ReportDetail extends Report { evidence: Record<string, unknown> }
export interface ReportList { reports: Report[]; total: number; page: number; page_size: number }
export const REPORT_STATUS = { pending: '待处理', handled: '已处理', dismissed: '不予处理' }
export const reportsApi = {
  create: async (target_type: ReportTarget, target_id: number, reason: string, description: string) => await apiClient.post('/reports', { target_type, target_id, reason, description }) as Report,
  list: async (admin: boolean, filter: string, page: number, signal?: AbortSignal) => await apiClient.get(`${admin ? '/admin/reports' : '/reports/mine'}?page=${page}&page_size=20${filter === 'appeals' ? '&appeal_pending=true' : filter === 'pending' ? '&status=pending' : ''}`, signal) as ReportList,
  detail: async (admin: boolean, id: number, signal?: AbortSignal) => await apiClient.get(`${admin ? '/admin' : ''}/reports/${id}`, signal) as ReportDetail,
  appeal: async (id: number, reason: string) => await apiClient.post(`/reports/${id}/appeal`, { reason }) as Report,
  resolve: async (id: number, status: Resolution, note: string, review: boolean) => await apiClient.post(`/admin/reports/${id}/${review ? 'appeal-review' : 'resolve'}`, { status, note }) as Report,
}
