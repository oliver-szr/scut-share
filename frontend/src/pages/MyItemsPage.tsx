import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { errorMessage } from '../api/client'
import { itemsApi } from '../api/items'
import type { Item } from '../api/items'
import { ItemForm } from '../components/ItemForm'
import { SiteHeader } from '../components/SiteHeader'

export function MyItemsPage() {
  const [items, setItems] = useState<Item[]>([])
  const [editingId, setEditingId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(true)
  useEffect(() => { itemsApi.mine().then(data => setItems(data.items)).catch(failure => setError(errorMessage(failure))).finally(() => setBusy(false)) }, [])
  const updateItem = (updated: Item) => { setItems(current => current.map(item => item.id === updated.id ? updated : item)); setEditingId(null) }
  return <div className="min-h-screen"><SiteHeader /><main className="page-width items-page"><div className="items-heading"><div><p className="eyebrow">MY ITEMS</p><h1>我的发布</h1><p>管理你发布的二手出售、免费借还和免费转赠物品。</p></div><Link className="primary-link" to="/items/new">发布物品 <span aria-hidden="true">↗</span></Link></div>{busy && <p className="auth-loading" role="status">正在加载…</p>}{error && <p className="form-error" role="alert">{error}</p>}{!busy && !error && (items.length ? <div className="items-grid">{items.map(item => editingId === item.id ? <article className="item-card" key={item.id}><ItemForm initial={item} onSuccess={updateItem} /></article> : <ItemCardMine key={item.id} item={item} onEdit={() => setEditingId(item.id)} />)}</div> : <div className="empty-state"><h2>还没有发布物品</h2><Link className="primary-link" to="/items/new">发布第一件物品</Link></div>)}</main></div>
}
function ItemCardMine({ item, onEdit }: { item: Item; onEdit: () => void }) { return <article className={`item-card ${item.status === 'withdrawn' ? 'withdrawn' : ''}`}><div className="item-card-body"><div className="item-card-meta"><span>{item.mode === 'sale' ? '二手出售' : item.mode === 'borrow' ? '免费借还' : '免费转赠'}</span><span>{item.status === 'published' ? '已发布' : '已下架'}</span></div><h3>{item.status === 'withdrawn' ? item.title : <Link to={`/items/${item.id}`}>{item.title}</Link>}</h3><p className="item-card-description">{item.description}</p>{item.status === 'withdrawn' ? <button className="text-button" type="button" onClick={onEdit}>编辑已下架物品</button> : <Link className="text-button" to={`/items/${item.id}`}>查看和编辑 →</Link>}</div></article> }
