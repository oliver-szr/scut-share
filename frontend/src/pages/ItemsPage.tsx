import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { ItemList } from '../api/items'
import { CAMPUSES, CATEGORIES, itemsApi } from '../api/items'
import { errorMessage } from '../api/client'
import { ItemCard } from '../components/ItemCard'
import { SiteHeader } from '../components/SiteHeader'

export function ItemsPage() {
  const [searchParams] = useSearchParams()
  const [list, setList] = useState<ItemList | null>(null)
  const [keyword, setKeyword] = useState(''); const [category, setCategory] = useState(''); const [campus, setCampus] = useState(''); const [mode, setMode] = useState(() => searchParams.get('mode') ?? '')
  const [page, setPage] = useState(1); const [error, setError] = useState<string | null>(null); const [busy, setBusy] = useState(false); const [reloadKey, setReloadKey] = useState(0)
  useEffect(() => { const controller = new AbortController(); setBusy(true); setError(null); itemsApi.list({ q: keyword, category, campus, mode, page, page_size: 12 }, controller.signal).then(setList).catch(failure => { if (!controller.signal.aborted) setError(errorMessage(failure)) }).finally(() => { if (!controller.signal.aborted) setBusy(false) }); return () => controller.abort() }, [keyword, category, campus, mode, page, reloadKey])
  const reset = () => { setKeyword(''); setCategory(''); setCampus(''); setMode(''); setPage(1) }
  return <div className="min-h-screen"><SiteHeader /><main className="page-width items-page"><div className="items-heading"><div><p className="eyebrow">SCUT SHARE · ITEMS</p><h1>物品广场</h1><p>找到身边正在流动的物品，也让闲置重新派上用场。</p></div><a className="primary-link" href="/items/new">发布物品 <span aria-hidden="true">↗</span></a></div>
    <form className="item-filters" onSubmit={e => { e.preventDefault(); setPage(1) }}><input aria-label="关键词" placeholder="搜索物品名称或描述" value={keyword} onChange={e => { setKeyword(e.target.value); setPage(1) }} /><select aria-label="流通方式" value={mode} onChange={e => { setMode(e.target.value); setPage(1) }}><option value="">全部方式</option><option value="sale">二手出售</option><option value="borrow">免费借还</option><option value="gift">免费转赠</option></select><select aria-label="分类" value={category} onChange={e => { setCategory(e.target.value); setPage(1) }}><option value="">全部分类</option>{CATEGORIES.map(value => <option key={value}>{value}</option>)}</select><select aria-label="校区" value={campus} onChange={e => { setCampus(e.target.value); setPage(1) }}><option value="">全部校区</option>{CAMPUSES.map(value => <option key={value}>{value}</option>)}</select><button type="button" className="text-button" onClick={reset}>重置</button></form>
    {busy && <p className="auth-loading" role="status">正在加载物品…</p>}{error && <p className="form-error" role="alert">{error} <button className="text-button" type="button" onClick={() => setReloadKey(value => value + 1)}>重试</button></p>}{!busy && !error && list && (list.items.length ? <><div className="items-grid">{list.items.map(item => <ItemCard key={item.id} item={item} />)}</div><div className="pagination"><span>共 {list.total} 件物品</span><button type="button" disabled={page <= 1} onClick={() => setPage(value => value - 1)}>上一页</button><span>第 {page} 页</span><button type="button" disabled={page * list.page_size >= list.total} onClick={() => setPage(value => value + 1)}>下一页</button></div></> : <div className="empty-state"><h2>还没有找到物品</h2><p>换个关键词或筛选条件试试，也可以发布第一件物品。</p><a className="primary-link" href="/items/new">发布物品</a></div>)}
  </main></div>
}
