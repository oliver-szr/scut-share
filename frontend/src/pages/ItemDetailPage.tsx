import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { errorMessage } from '../api/client'
import { imageUrl, itemsApi } from '../api/items'
import type { Item } from '../api/items'
import { tradesApi } from '../api/trades'
import { useAuth } from '../auth/AuthContext'
import { ItemForm } from '../components/ItemForm'
import { SiteHeader } from '../components/SiteHeader'
import { BorrowRequestForm } from '../components/BorrowRequestForm'
import { ContactButton } from '../components/ContactButton'
import { ReportButton } from '../components/ReportButton'
import { PriceReference } from '../components/PriceReference'
import { giftsApi } from '../api/gifts'

export function ItemDetailPage() {
  const { id } = useParams()
  const itemId = Number(id)
  const { state } = useAuth()
  const [item, setItem] = useState<Item | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState('')
  const [applied, setApplied] = useState(false)
  const [borrowFormOpen, setBorrowFormOpen] = useState(false)
  const [borrowApplied, setBorrowApplied] = useState(false)
  const [giftApplied, setGiftApplied] = useState(false)
  const submitting = useRef(false)
  useEffect(() => {
    const controller = new AbortController()
    setItem(null); setError(null); setApplied(false); setEditing(false); setNote('')
    setBorrowFormOpen(false); setBorrowApplied(false)
    setGiftApplied(false)
    if (!Number.isInteger(itemId) || itemId < 1) { setError('物品不存在。'); return }
    itemsApi.get(itemId, controller.signal).then(setItem).catch(failure => { if (!controller.signal.aborted) setError(errorMessage(failure)) })
    return () => controller.abort()
  }, [itemId])
  const withdraw = async () => {
    if (!item || submitting.current || !window.confirm('确定下架这件物品吗？')) return
    submitting.current = true; setBusy(true); setError(null)
    try { setItem(await itemsApi.withdraw(item.id)) }
    catch (failure) { setError(errorMessage(failure)) }
    finally { submitting.current = false; setBusy(false) }
  }
  const purchase = async () => {
    if (!item || submitting.current || applied) return
    submitting.current = true; setBusy(true); setError(null)
    try { await tradesApi.create(item.id, note); setApplied(true) }
    catch (failure) { setError(errorMessage(failure)) }
    finally { submitting.current = false; setBusy(false) }
  }
  const owner = state.status === 'authenticated' && state.user.id === item?.owner_id
  const claimGift = async () => {
    if (!item || submitting.current || giftApplied) return
    submitting.current = true; setBusy(true); setError(null)
    try { await giftsApi.create(item.id, note); setGiftApplied(true) }
    catch (failure) { setError(errorMessage(failure)) }
    finally { submitting.current = false; setBusy(false) }
  }
  return <div className="min-h-screen"><SiteHeader /><main className="page-width detail-page">
    <Link className="back-link" to="/items">← 返回物品广场</Link>
    {error && <p className="form-error" role="alert">{error}</p>}
    {!item && !error && <p className="auth-loading" role="status">正在加载物品…</p>}
    {item && (editing ? <section className="auth-panel item-editor"><p className="eyebrow">EDIT ITEM</p><h1>编辑物品</h1><ItemForm initial={item} onSuccess={updated => { setItem(updated); setEditing(false) }} /></section> :
      <article className="item-detail">
        <div className="detail-gallery">{item.images.length ? item.images.map(image => <img key={image.id} src={imageUrl(image.url)} alt={item.title} />) : <div className="detail-placeholder">{item.mode === 'sale' ? '↗' : '⇄'}</div>}</div>
        <div className="detail-copy">
          <div className="item-card-meta"><span>{item.category}</span><span>{item.campus}</span><span>{item.status === 'withdrawn' ? '已下架' : item.mode === 'sale' ? '二手出售' : item.mode === 'borrow' ? '免费借还' : '免费转赠'}</span></div>
          <h1>{item.title}</h1><p className="detail-owner">发布者：{item.owner.nickname} · {new Date(item.created_at).toLocaleDateString('zh-CN')}</p>
          {state.status === 'authenticated' && <ReportButton key={item.id} target="item" id={item.id} />}
          <p className="detail-description">{item.description}</p>
          {item.mode === 'sale' ? <strong className="detail-price">¥{((item.price_cents ?? 0) / 100).toFixed(2)}</strong> : item.mode === 'borrow' ? <div className="borrow-note"><strong>借用说明</strong><p>{item.borrow_note}</p></div> : <strong className="detail-price">免费转赠</strong>}
          {item.interest_tags.length > 0 && <div className="tag-list detail-tags">{item.interest_tags.map(tag => <span key={tag}>{tag}</span>)}</div>}
          {item.mode === 'sale' && <PriceReference itemId={item.id} />}
          {item.mode === 'gift' && <div className="purchase-panel">
            {item.availability === 'reserved' && <p role="status">已同意领取，待交接</p>}{item.availability === 'gifted' && <p role="status">已赠送</p>}
            {giftApplied ? <p className="form-success" role="status">领取申请已提交，等待物主处理。<Link to="/my-gifts">查看我的转赠 →</Link></p> : item.status === 'published' && item.availability === 'available' && !owner && (state.status === 'authenticated' ? <form onSubmit={event => { event.preventDefault(); void claimGift() }}>
              <div className="form-field"><label htmlFor="gift-note">领取备注（选填）</label><textarea id="gift-note" maxLength={300} disabled={busy} value={note} onChange={event => setNote(event.target.value)} /></div><button className="form-submit" disabled={busy}>{busy ? '正在提交…' : '申请领取'}</button>
            </form> : state.status === 'anonymous' && <Link to="/login">登录后申请领取</Link>)}
            <p className="field-hint">免费转赠，双方通过申请备注和已有联系方式协商线下交接。<Link to="/my-gifts">我的转赠</Link></p>
          </div>}
          {item.mode === 'sale' && <div className="purchase-panel">
            {item.status === 'published' && item.availability === 'available' && !owner && (state.status === 'authenticated'
              ? <ContactButton context="item" id={item.id} label="联系卖家" />
              : state.status === 'anonymous' && <Link to="/login">登录后联系卖家</Link>)}
            {item.availability === 'reserved' && <p className="form-success" role="status">已预留</p>}
            {item.availability === 'sold' && <p className="form-success" role="status">已售出</p>}
            {applied ? <p className="form-success" role="status">购买意向已提交，等待卖家处理。<Link to="/my-trades">查看我的交易 →</Link></p> :
              item.status === 'published' && item.availability === 'available' && !owner && <>
                {state.status === 'authenticated' ? <form onSubmit={event => { event.preventDefault(); void purchase() }}>
                  <div className="form-field"><label htmlFor="purchase-note">购买备注（选填）</label><textarea id="purchase-note" maxLength={300} value={note} onChange={event => setNote(event.target.value)} disabled={busy} /></div>
                  <button className="form-submit" disabled={busy}>{busy ? '正在提交…' : '我想购买'}</button>
                </form> : state.status === 'anonymous' && <Link className="primary-link" to="/login">登录后购买</Link>}
              </>}
            <p className="field-hint">平台只记录交易状态，付款与交付由双方线下完成。<Link to="/my-trades">我的交易</Link></p>
          </div>}
          {item.mode === 'borrow' && item.status === 'published' && <div className="purchase-panel">
            {item.availability === 'reserved' && <p className="form-success" role="status">已同意申请，待交接</p>}
            {item.availability === 'borrowed' && <p className="form-success" role="status">借用中</p>}
            {item.availability === 'return_pending' && <p className="form-success" role="status">待双方确认归还</p>}
            {borrowApplied ? <p className="form-success" role="status">借用申请已提交，等待物主处理。<Link to="/my-borrows">查看我的借还 →</Link></p> :
              item.availability === 'available' && !owner && (state.status === 'authenticated' ?
                borrowFormOpen ? <BorrowRequestForm itemId={item.id} onSuccess={() => setBorrowApplied(true)} /> : <button className="form-submit" type="button" onClick={() => setBorrowFormOpen(true)}>申请免费借用</button>
                : state.status === 'anonymous' && <Link className="primary-link" to="/login">登录后申请借用</Link>)}
            <p className="field-hint">免费借还，物主同意申请后可在借还记录中联系对方，协商线下交接。<Link to="/my-borrows">我的借还</Link></p>
          </div>}
          {item.mode === 'borrow' && item.status === 'withdrawn' && <p className="form-success" role="status">该物品已下架，暂不可申请借用。</p>}
          {owner && <div className="owner-actions"><button type="button" onClick={() => setEditing(true)}>编辑</button>{item.status === 'published' && item.availability === 'available' && <button type="button" onClick={() => void withdraw()} disabled={busy}>下架</button>}</div>}
        </div>
      </article>)}
  </main></div>
}
