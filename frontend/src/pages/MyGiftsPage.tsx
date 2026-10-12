import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { errorMessage } from '../api/client'
import { GIFT_STATUS, giftsApi } from '../api/gifts'
import type { GiftAction, GiftList } from '../api/gifts'
import { imageUrl } from '../api/items'
import { SiteHeader } from '../components/SiteHeader'

export function MyGiftsPage() {
  const [role, setRole] = useState<'owner' | 'recipient'>('recipient')
  const [data, setData] = useState<GiftList | null>(null)
  const [page, setPage] = useState(1)
  const [revision, setRevision] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const submitting = useRef(false)
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null); setData(null)
    giftsApi.mine(role, page, controller.signal).then(result => { if (!controller.signal.aborted) setData(result) })
      .catch(failure => { if (!controller.signal.aborted) setError(errorMessage(failure)) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [role, page, revision])
  const act = async (id: number, action: GiftAction) => {
    if (submitting.current) return
    if (action === 'confirm' && !window.confirm('请确认已在线下交出或收到物品。确认后不能单方面取消。')) return
    submitting.current = true; setBusy(true); setError(null); setFeedback(null)
    try {
      const result = await giftsApi.action(id, action)
      setFeedback(action === 'confirm' ? result.status === 'completed' ? '双方已确认，转赠完成。' : '你的交接确认已记录，等待对方确认。' : action === 'approve' ? '已同意申请，请双方协商线下交接。' : action === 'reject' ? '申请已拒绝。' : '申请已取消。')
      setRevision(value => value + 1)
    } catch (failure) { setError(errorMessage(failure)) }
    finally { submitting.current = false; setBusy(false) }
  }
  return <div className="min-h-screen"><SiteHeader /><main className="page-width items-page">
    <div className="items-heading"><div><p className="eyebrow">MY GIFTS</p><h1>我的转赠</h1><p>免费领取，线下交接，双方确认后完成；请通过备注和双方已有联系方式协商。</p></div><Link className="primary-link" to="/items?mode=gift">浏览免费转赠 →</Link></div>
    <div className="mode-toggle trade-tabs">{(['recipient', 'owner'] as const).map(value => <button key={value} aria-pressed={role === value} className={role === value ? 'active' : ''} disabled={busy} onClick={() => { setRole(value); setPage(1); setFeedback(null) }}>{value === 'recipient' ? '我申请领取的' : '我赠出的'}</button>)}</div>
    <button className="text-button" disabled={busy || loading} onClick={() => setRevision(value => value + 1)}>刷新转赠</button>
    {error && <p className="form-error" role="alert">{error}</p>}{feedback && <p className="form-success" role="status">{feedback}</p>}{loading && <p role="status">正在加载转赠…</p>}
    <div className="trade-list">{data?.gifts.map(gift => {
      const confirmed = Boolean(gift.owner_confirmed_at || gift.recipient_confirmed_at)
      const mineConfirmed = role === 'owner' ? gift.owner_confirmed_at : gift.recipient_confirmed_at
      return <article className="trade-card-row" key={gift.id} aria-label={`转赠 ${gift.id}`}>
        <Link className="trade-image" to={`/items/${gift.item_id}`}>{gift.item.images[0] ? <img src={imageUrl(gift.item.images[0].url)} alt={gift.item.title} /> : <span>♡</span>}</Link>
        <div className="trade-copy"><p>{GIFT_STATUS[gift.status]}</p><h2><Link to={`/items/${gift.item_id}`}>{gift.item.title}</Link></h2><p>{role === 'owner' ? `领取人：${gift.recipient.nickname}` : `物主：${gift.owner.nickname}`}</p><p>免费转赠 · 无价格、租金或押金</p>{gift.note && <p className="trade-note">备注：{gift.note}</p>}
          {gift.status === 'approved' && <p>交付：{gift.owner_confirmed_at ? '已确认' : '未确认'} · 领取：{gift.recipient_confirmed_at ? '已确认' : '未确认'}</p>}
          {gift.completed_at && <p>完成时间：{new Date(gift.completed_at).toLocaleString('zh-CN')}</p>}
          <div className="owner-actions trade-actions">
            {gift.status === 'pending' && (role === 'recipient' ? <button disabled={busy} onClick={() => void act(gift.id, 'cancel')}>取消领取申请</button> : <><button disabled={busy} onClick={() => void act(gift.id, 'approve')}>同意领取</button><button disabled={busy} onClick={() => void act(gift.id, 'reject')}>拒绝领取</button></>)}
            {gift.status === 'approved' && <>{!confirmed && <button disabled={busy} onClick={() => void act(gift.id, 'cancel')}>取消待交接</button>}{!mineConfirmed && <button disabled={busy} onClick={() => void act(gift.id, 'confirm')}>{role === 'owner' ? '确认已交付物品' : '确认已领取物品'}</button>}</>}
          </div>
        </div>
      </article>
    })}</div>
    {!loading && !error && data?.total === 0 && <p className="empty-state">暂无转赠记录。</p>}
    {data && data.total > data.page_size && <div className="pagination"><button disabled={page === 1 || busy} onClick={() => setPage(value => value - 1)}>上一页</button><span>{page}</span><button disabled={page * data.page_size >= data.total || busy} onClick={() => setPage(value => value + 1)}>下一页</button></div>}
  </main></div>
}
