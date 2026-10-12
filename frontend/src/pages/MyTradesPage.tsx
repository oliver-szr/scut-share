import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { errorMessage } from '../api/client'
import { imageUrl } from '../api/items'
import { TRADE_STATUS_LABELS, tradesApi } from '../api/trades'
import type { TradeAction, TradeList, TradeRole } from '../api/trades'
import { SiteHeader } from '../components/SiteHeader'
import { ContactButton } from '../components/ContactButton'
import { ReportButton } from '../components/ReportButton'

export function MyTradesPage() {
  const [role, setRole] = useState<TradeRole>('buyer')
  const [page, setPage] = useState(1)
  const [revision, setRevision] = useState(0)
  const [data, setData] = useState<TradeList | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const submitting = useRef(false)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError(null); setData(null)
    tradesApi.mine(role, page, controller.signal).then(result => {
      if (!controller.signal.aborted) setData(result)
    }).catch(failure => { if (!controller.signal.aborted) setError(errorMessage(failure)) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [role, page, revision])

  const act = async (id: number, action: TradeAction) => {
    if (submitting.current) return
    if (action === 'confirm' && !window.confirm('请确认双方已在线下完成付款和商品交付。确认后将不能单方面取消交易。')) return
    submitting.current = true; setBusy(id); setError(null); setMessage(null)
    try {
      const updated = await tradesApi.action(id, action)
      setData(current => current && ({ ...current, trades: current.trades.map(trade => trade.id === id ? updated : trade) }))
      setMessage(action === 'accept' ? '已预留，可联系对方协商线下付款和交付。'
        : action === 'confirm' ? updated.status === 'completed' ? '双方已确认，交易完成，商品已售出。' : '你的成交确认已记录，等待对方确认。'
        : action === 'reject' ? '申请已拒绝。' : '交易已取消。')
      setRevision(value => value + 1)
    } catch (failure) { setError(errorMessage(failure)) }
    finally { submitting.current = false; setBusy(null) }
  }

  return <div className="min-h-screen"><SiteHeader /><main className="page-width items-page">
    <div className="items-heading"><div><p className="eyebrow">MY TRADES</p><h1>我的交易</h1><p>付款和商品交付在线下完成，双方确认后才记录为已成交。</p></div><Link className="primary-link" to="/items?mode=sale">浏览二手出售 →</Link></div>
    <div className="mode-toggle trade-tabs" aria-label="交易视图">{(['buyer', 'seller'] as const).map(value => <button key={value} type="button" className={role === value ? 'active' : ''} aria-pressed={role === value} disabled={busy !== null} onClick={() => { setRole(value); setPage(1); setMessage(null) }}>{value === 'buyer' ? '我买入的' : '我卖出的'}</button>)}</div>
    {message && <p className="form-success" role="status">{message}</p>}
    {error && <div className="form-error" role="alert">{error} <button className="text-button" disabled={busy !== null} onClick={() => setRevision(value => value + 1)}>刷新交易</button></div>}
    {loading && <p className="auth-loading" role="status">正在加载交易…</p>}
    {!loading && data && (data.trades.length ? <div className="trade-list">{data.trades.map(trade => {
      const mineConfirmed = role === 'buyer' ? trade.buyer_confirmed_at : trade.seller_confirmed_at
      const confirmed = trade.buyer_confirmed_at !== null || trade.seller_confirmed_at !== null
      return <article className="trade-card-row" key={trade.id} aria-label={`交易 ${trade.id}`}>
        <Link className="trade-image" to={`/items/${trade.item_id}`}>{trade.item.images[0] ? <img src={imageUrl(trade.item.images[0].url)} alt={trade.item.title} /> : <span aria-hidden="true">↗</span>}</Link>
        <div className="trade-copy"><div className="item-card-meta"><span>{TRADE_STATUS_LABELS[trade.status]}</span><span>交易 #{trade.id}</span></div>
          <h2><Link to={`/items/${trade.item_id}`}>{trade.item.title}</Link></h2>
          <p>{role === 'buyer' ? `卖家：${trade.seller.nickname}` : `买家：${trade.buyer.nickname}`}</p>
          <strong>意向价格 ¥{(trade.price_cents_snapshot / 100).toFixed(2)}</strong>
          {trade.note && <p className="trade-note">备注：{trade.note}</p>}
          {trade.status === 'reserved' && <><p className="field-hint">买方：{trade.buyer_confirmed_at ? '已确认' : '未确认'} · 卖方：{trade.seller_confirmed_at ? '已确认' : '未确认'}</p><p className="field-hint">{confirmed ? '已有一方确认，不能单方面取消；如有分歧请双方联系解决，可提交举报请求人工处理。' : '预留后可联系对方协商线下付款和交付。'}</p></>}
          {trade.completed_at && <p className="field-hint">成交时间：{new Date(trade.completed_at).toLocaleString('zh-CN')}</p>}
          <div className="owner-actions trade-actions">
            <ReportButton target="trade" id={trade.id} />
            {(['pending', 'reserved', 'completed'] as const).some(status => status === trade.status) && <ContactButton context="trade" id={trade.id} />}
            {trade.status === 'pending' && (role === 'buyer' ? <button disabled={busy !== null} onClick={() => void act(trade.id, 'cancel')}>取消申请</button> : <><button disabled={busy !== null} onClick={() => void act(trade.id, 'accept')}>接受申请</button><button disabled={busy !== null} onClick={() => void act(trade.id, 'reject')}>拒绝申请</button></>)}
            {trade.status === 'reserved' && <>{!confirmed && <button disabled={busy !== null} onClick={() => void act(trade.id, 'cancel')}>取消预留</button>}{!mineConfirmed && <button disabled={busy !== null} onClick={() => void act(trade.id, 'confirm')}>确认交易完成</button>}</>}
            {busy === trade.id && <span role="status">正在提交…</span>}
          </div>
        </div>
      </article>
    })}</div> : !error && <div className="empty-state"><h2>暂无交易记录</h2><p>购买申请与收到的申请会显示在这里。</p></div>)}
    {!loading && data && data.total > data.page_size && <div className="pagination"><button disabled={page === 1 || busy !== null} onClick={() => setPage(value => value - 1)}>上一页</button><span>第 {page} 页 · 共 {data.total} 笔</span><button disabled={page * data.page_size >= data.total || busy !== null} onClick={() => setPage(value => value + 1)}>下一页</button></div>}
  </main></div>
}
