import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { errorMessage } from '../api/client'
import { REPORT_STATUS, reportsApi } from '../api/reports'
import type { ReportDetail, ReportList, Resolution } from '../api/reports'
import { useAuth } from '../auth/AuthContext'
import { SiteHeader } from '../components/SiteHeader'

const EVIDENCE_LABELS: Record<string, string> = { item_id: '物品编号', title: '物品名称', description: '当时描述', mode: '流通方式', owner: '物主', record_id: '记录编号', status: '当时状态', note: '申请备注', price_cents_snapshot: '意向价格（分）', seller_id: '卖家编号', buyer_id: '买家编号', owner_id: '物主编号', borrower_id: '借用人编号', expected_return_at: '预计归还', message_id: '消息编号', conversation_id: '会话编号', sender_id: '发送者编号', content: '所举报消息', created_at: '消息时间' }

export function ReportsPage({ admin = false }: { admin?: boolean }) {
  const { state } = useAuth()
  const allowed = !admin || state.user?.is_admin === true
  const [params, setParams] = useSearchParams()
  const rawId = params.get('report')
  const selectedId = rawId && /^[1-9]\d*$/.test(rawId) && Number.isSafeInteger(Number(rawId)) ? Number(rawId) : null
  const [filter, setFilter] = useState(admin ? 'pending' : 'all')
  const [page, setPage] = useState(1)
  const [revision, setRevision] = useState(0)
  const [list, setList] = useState<ReportList | null>(null)
  const [detail, setDetail] = useState<ReportDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const [decision, setDecision] = useState<Resolution>('handled')
  const [busy, setBusy] = useState(false)
  const submitting = useRef(false)
  useEffect(() => {
    if (!allowed) return
    const controller = new AbortController(); setLoading(true); setError(null); setList(null); setDetail(null)
    Promise.all([reportsApi.list(admin, filter, page, controller.signal), selectedId ? reportsApi.detail(admin, selectedId, controller.signal) : Promise.resolve(null)])
      .then(([rows, selected]) => { if (!controller.signal.aborted) { setList(rows); setDetail(selected) } })
      .catch(failure => { if (!controller.signal.aborted) setError(errorMessage(failure)) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [admin, allowed, filter, page, selectedId, revision])
  useEffect(() => { setNote(''); setFeedback(null) }, [selectedId])
  const submit = async () => {
    if (!detail || submitting.current || !note.trim()) return
    submitting.current = true; setBusy(true); setError(null); setFeedback(null)
    try {
      if (admin) await reportsApi.resolve(detail.id, decision, note.trim(), detail.appeal?.status === 'pending')
      else await reportsApi.appeal(detail.id, note.trim())
      setNote(''); setFeedback(admin ? '处理结果已记录。' : '复核申诉已提交。'); setRevision(value => value + 1)
    } catch (failure) { setError(errorMessage(failure)) }
    finally { submitting.current = false; setBusy(false) }
  }
  return <div className="min-h-screen"><SiteHeader /><main className="page-width items-page">
    <div className="items-heading"><div><p className="eyebrow">REPORTS</p><h1>{admin ? '举报管理' : '我的举报与申诉'}</h1><p>人工记录和反馈处理结果，交易与借还状态需按原流程确认。</p></div></div>
    {!allowed ? <p className="form-error" role="alert">仅管理员可以访问。</p> : <>
      {admin && <div className="owner-actions">{[['pending', '待处理'], ['appeals', '待复核申诉'], ['all', '全部']].map(([value, label]) => <button key={value} disabled={busy} aria-pressed={filter === value} onClick={() => { setFilter(value); setPage(1) }}>{label}</button>)}</div>}
      <button className="text-button" disabled={loading || busy} onClick={() => setRevision(value => value + 1)}>刷新记录</button>
      {error && <p className="form-error" role="alert">{error}</p>}{feedback && <p className="form-success" role="status">{feedback}</p>}
      {loading && <p role="status">正在加载举报…</p>}
      <div className="report-layout"><section aria-label="举报列表">
        {list?.reports.map(row => <button className={`report-entry ${row.id === selectedId ? 'active' : ''}`} disabled={busy} key={row.id} onClick={() => setParams({ report: String(row.id) })}><strong>举报 #{row.id} · {row.reason}</strong><span>{REPORT_STATUS[row.status]}{row.appeal?.status === 'pending' ? ' · 待复核' : ''}</span><time>{new Date(row.created_at).toLocaleString('zh-CN')}</time></button>)}
        {list?.total === 0 && <p className="field-hint">暂无举报记录。</p>}
        {list && list.total > list.page_size && <div className="pagination"><button disabled={page === 1 || busy} onClick={() => setPage(value => value - 1)}>上一页</button><span>{page}</span><button disabled={page * list.page_size >= list.total || busy} onClick={() => setPage(value => value + 1)}>下一页</button></div>}
      </section><section className="report-detail" aria-label="举报详情">{detail ? <>
        <h2>举报 #{detail.id} · {REPORT_STATUS[detail.status]}</h2><p>{detail.reason}</p><p className="detail-description">{detail.description}</p>
        <h3>提交时的关联证据</h3><dl className="report-evidence">{Object.entries(detail.evidence).map(([key, value]) => <div key={key}><dt>{EVIDENCE_LABELS[key] ?? '关联信息'}</dt><dd>{value === null ? '无' : typeof value === 'object' ? String((value as { nickname?: string }).nickname ?? '') : String(value)}</dd></div>)}</dl>
        {detail.resolution_note && <p>处理说明：{detail.resolution_note}</p>}
        {detail.appeal && <><h3>复核申诉</h3><p>{detail.appeal.reason}</p><p>{detail.appeal.status === 'pending' ? '等待管理员复核' : `复核结果：${detail.appeal.decision ? REPORT_STATUS[detail.appeal.decision] : ''} · ${detail.appeal.review_note}`}</p></>}
        {(admin ? detail.status === 'pending' || detail.appeal?.status === 'pending' : detail.status !== 'pending' && !detail.appeal) && <form className="report-form" onSubmit={event => { event.preventDefault(); void submit() }}>
          {admin && <><label htmlFor="resolution">处理结论</label><select id="resolution" value={decision} disabled={busy} onChange={event => setDecision(event.target.value as Resolution)}><option value="handled">已处理</option><option value="dismissed">不予处理</option></select></>}
          <label htmlFor="report-note">{admin ? '处理说明' : '复核申诉理由（仅可提交一次）'}</label><textarea id="report-note" required maxLength={1000} disabled={busy} value={note} onChange={event => setNote(event.target.value)} />
          <button className="contact-button" disabled={busy || !note.trim()}>{busy ? '正在提交…' : admin ? detail.appeal?.status === 'pending' ? '提交复核结果' : '提交处理结果' : '提交复核申诉'}</button>
        </form>}
      </> : !loading && <p className="field-hint">选择举报查看详情。</p>}</section></div>
    </>}
  </main></div>
}
