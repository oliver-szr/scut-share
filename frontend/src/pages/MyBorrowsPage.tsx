import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { errorMessage } from '../api/client'
import { imageUrl } from '../api/items'
import { BORROW_STATUS_LABELS, borrowsApi } from '../api/borrows'
import type { BorrowAction, BorrowList, BorrowRole } from '../api/borrows'
import { SiteHeader } from '../components/SiteHeader'
import { ContactButton } from '../components/ContactButton'
import { ReportButton } from '../components/ReportButton'

export function MyBorrowsPage() {
  const [role, setRole] = useState<BorrowRole>('borrower')
  const [page, setPage] = useState(1)
  const [revision, setRevision] = useState(0)
  const [data, setData] = useState<BorrowList | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const submitting = useRef(false)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError(null); setData(null)
    borrowsApi.mine(role, page, controller.signal).then(result => { if (!controller.signal.aborted) setData(result) })
      .catch(failure => { if (!controller.signal.aborted) setError(errorMessage(failure)) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [role, page, revision])
  const act = async (id: number, action: BorrowAction) => {
    if (submitting.current) return
    if (action === 'confirm-handover' && !window.confirm('请确认你已在线下交出或收到物品。确认后不能单方面取消。')) return
    if (action === 'confirm-return' && !window.confirm('请确认你已在线下归还或收到归还物品。双方确认后物品将恢复可借。')) return
    submitting.current = true; setBusy(id); setError(null); setMessage(null)
    try {
      const updated = await borrowsApi.action(id, action)
      setMessage(action === 'approve' ? '申请已同意，可联系对方协商线下交接。'
        : action === 'confirm-handover' ? updated.status === 'borrowed' ? '双方已确认借出，物品借用中。' : '你的交接确认已记录，等待对方确认。'
        : action === 'confirm-return' ? updated.status === 'completed' ? '双方已确认归还，物品重新可借，历史记录已保留。' : '你的归还确认已记录，等待对方确认。'
        : action === 'reject' ? '申请已拒绝。' : '借用申请已取消。')
      setRevision(value => value + 1)
    } catch (failure) { setError(errorMessage(failure)) }
    finally { submitting.current = false; setBusy(null) }
  }
  return <div className="min-h-screen"><SiteHeader /><main className="page-width items-page">
    <div className="items-heading"><div><p className="eyebrow">MY BORROWS</p><h1>我的借还</h1><p>免费借用，线下交接；借出与归还均需双方确认。</p></div><Link className="primary-link" to="/items?mode=borrow">浏览免费借还 →</Link></div>
    <div className="mode-toggle trade-tabs" aria-label="借还视图">{(['borrower', 'owner'] as const).map(value => <button key={value} type="button" className={role === value ? 'active' : ''} aria-pressed={role === value} disabled={busy !== null} onClick={() => { setRole(value); setPage(1); setMessage(null) }}>{value === 'borrower' ? '我借入的' : '我借出的'}</button>)}</div>
    <button className="text-button" disabled={busy !== null || loading} onClick={() => setRevision(value => value + 1)}>刷新借还</button>
    {message && <p className="form-success" role="status">{message}</p>}
    {error && <p className="form-error" role="alert">{error}</p>}
    {loading && <p className="auth-loading" role="status">正在加载借还…</p>}
    {!loading && data && (data.borrows.length ? <div className="trade-list">{data.borrows.map(borrow => {
      const mineHandover = role === 'owner' ? borrow.owner_handover_confirmed_at : borrow.borrower_handover_confirmed_at
      const mineReturn = role === 'owner' ? borrow.owner_return_confirmed_at : borrow.borrower_return_confirmed_at
      const handoverStarted = borrow.owner_handover_confirmed_at !== null || borrow.borrower_handover_confirmed_at !== null
      const overdue = (borrow.status === 'borrowed' || borrow.status === 'return_pending') && new Date(borrow.expected_return_at).getTime() < Date.now()
      return <article className="trade-card-row" key={borrow.id} aria-label={`借还 ${borrow.id}`}>
        <Link className="trade-image" to={`/items/${borrow.item_id}`}>{borrow.item.images[0] ? <img src={imageUrl(borrow.item.images[0].url)} alt={borrow.item.title} /> : <span aria-hidden="true">⇄</span>}</Link>
        <div className="trade-copy"><div className="item-card-meta"><span>{BORROW_STATUS_LABELS[borrow.status]}</span><span>免费借还 #{borrow.id}</span>{overdue && <span className="overdue-badge">已逾期</span>}</div>
          <h2><Link to={`/items/${borrow.item_id}`}>{borrow.item.title}</Link></h2>
          <p>{role === 'borrower' ? `物主：${borrow.owner.nickname}` : `借用人：${borrow.borrower.nickname}`}</p>
          <p>预计开始：{new Date(borrow.requested_start_at).toLocaleString('zh-CN')}</p>
          <p>预计归还：{new Date(borrow.expected_return_at).toLocaleString('zh-CN')}</p>
          {borrow.note && <p className="trade-note">备注：{borrow.note}</p>}
          {borrow.status === 'approved' && <><p className="field-hint">借出确认 · 物主：{borrow.owner_handover_confirmed_at ? '已确认' : '未确认'} · 借用人：{borrow.borrower_handover_confirmed_at ? '已确认' : '未确认'}</p><p className="field-hint">{handoverStarted ? '已有一方确认交接，不能单方面取消；请等待对方确认。' : '可联系对方协商交接时间和地点，交接后各自确认。'}</p></>}
          {(borrow.status === 'borrowed' || borrow.status === 'return_pending') && <p className="field-hint">归还确认 · 物主：{borrow.owner_return_confirmed_at ? '已确认' : '未确认'} · 借用人：{borrow.borrower_return_confirmed_at ? '已确认' : '未确认'}。双方确认后才恢复可借；如有分歧请双方联系解决，可提交举报请求人工处理。</p>}
          {borrow.borrowed_at && <p className="field-hint">实际借出确认：{new Date(borrow.borrowed_at).toLocaleString('zh-CN')}</p>}
          {borrow.completed_at && <p className="field-hint">归还完成：{new Date(borrow.completed_at).toLocaleString('zh-CN')}</p>}
          <div className="owner-actions trade-actions">
            <ReportButton target="borrow" id={borrow.id} />
            {(['approved', 'borrowed', 'return_pending', 'completed'] as const).some(status => status === borrow.status) && <ContactButton context="borrow" id={borrow.id} />}
            {borrow.status === 'pending' && (role === 'borrower' ? <button disabled={busy !== null} onClick={() => void act(borrow.id, 'cancel')}>取消申请</button> : <><button disabled={busy !== null} onClick={() => void act(borrow.id, 'approve')}>同意申请</button><button disabled={busy !== null} onClick={() => void act(borrow.id, 'reject')}>拒绝申请</button></>)}
            {borrow.status === 'approved' && <>{!handoverStarted && <button disabled={busy !== null} onClick={() => void act(borrow.id, 'cancel')}>取消待交接</button>}{!mineHandover && <button disabled={busy !== null} onClick={() => void act(borrow.id, 'confirm-handover')}>{role === 'owner' ? '确认已交出物品' : '确认已收到物品'}</button>}</>}
            {(borrow.status === 'borrowed' || borrow.status === 'return_pending') && !mineReturn && <button disabled={busy !== null} onClick={() => void act(borrow.id, 'confirm-return')}>{role === 'owner' ? '确认已收到归还物品' : '确认已归还物品'}</button>}
            {busy === borrow.id && <span role="status">正在提交…</span>}
          </div>
        </div>
      </article>
    })}</div> : !error && <div className="empty-state"><h2>暂无借还记录</h2><p>申请借用与收到的申请会显示在这里。</p></div>)}
    {!loading && data && data.total > data.page_size && <div className="pagination"><button disabled={page === 1 || busy !== null} onClick={() => setPage(value => value - 1)}>上一页</button><span>第 {page} 页 · 共 {data.total} 笔</span><button disabled={page * data.page_size >= data.total || busy !== null} onClick={() => setPage(value => value + 1)}>下一页</button></div>}
  </main></div>
}
