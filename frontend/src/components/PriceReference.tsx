import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiClient, errorMessage } from '../api/client'
import type { Campus } from '../api/items'

interface Reference {
  items: { id: number; title: string; campus: Campus; price_cents: number }[]
  sample_count: number; min_price_cents: number | null; max_price_cents: number | null
}
const disclaimer = '仅供参考，展示的是当前挂牌价，不代表实际成交价或公允价格。'

export function PriceReference({ itemId }: { itemId: number }) {
  const [sameCampus, setSameCampus] = useState(false)
  const [data, setData] = useState<Reference | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null); setData(null)
    apiClient.get(`/items/${itemId}/price-reference?same_campus=${sameCampus}`, controller.signal)
      .then(result => {
        if (typeof result !== 'object' || result === null || !('items' in result) || !Array.isArray(result.items) || !('sample_count' in result)) throw new Error('Invalid price reference')
        if (!controller.signal.aborted) setData(result as Reference)
      }).catch(failure => { if (!controller.signal.aborted) setError(errorMessage(failure)) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [itemId, sameCampus, revision])
  return <section className="price-reference" aria-label="挂牌价格参考"><h2>挂牌价格参考</h2>
    <p className="field-hint">同类且标题含相同字词的在售商品，最多展示 8 件；未核验同品牌、型号或成色。</p>
    <label><input type="checkbox" checked={sameCampus} onChange={event => setSameCampus(event.target.checked)} />仅看同校区</label>
    {loading && <p role="status">正在加载参考…</p>}
    {error && <p className="form-error" role="alert">{error} <button className="text-button" onClick={() => setRevision(value => value + 1)}>重试价格参考</button></p>}
    {data && <>{data.sample_count >= 3 && data.min_price_cents !== null && data.max_price_cents !== null ? <strong>所列 {data.sample_count} 件挂牌价范围：¥{(data.min_price_cents / 100).toFixed(2)}～¥{(data.max_price_cents / 100).toFixed(2)}</strong> : <p>参考数据不足</p>}
      <ul>{data.items.map(row => <li key={row.id}><Link to={`/items/${row.id}`}>{row.title}</Link><span>¥{(row.price_cents / 100).toFixed(2)} · {row.campus}</span></li>)}</ul></>}
    <p className="field-hint">{disclaimer}</p>
  </section>
}
