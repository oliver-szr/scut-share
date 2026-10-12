import { Link } from 'react-router-dom'
import { imageUrl } from '../api/items'
import type { Item } from '../api/items'

export function ItemCard({ item }: { item: Item }) {
  return <article className="item-card">
    <Link to={`/items/${item.id}`} className="item-card-image">
      {item.images[0] ? <img src={imageUrl(item.images[0].url)} alt="" /> : <span aria-hidden="true">{item.mode === 'sale' ? '↗' : '⇄'}</span>}
    </Link>
    <div className="item-card-body">
      <div className="item-card-meta"><span>{item.category}</span><span>{item.campus}</span></div>
      {item.mode === 'sale' && item.availability !== 'available' && <p className="field-hint">{item.availability === 'sold' ? '已售出' : item.availability === 'reserved' ? '已预留' : '已下架'}</p>}
      {item.mode === 'borrow' && <p className="field-hint">{item.availability === 'available' ? '可借' : item.availability === 'reserved' ? '待交接' : item.availability === 'borrowed' ? '借用中' : item.availability === 'return_pending' ? '待双方确认归还' : '已下架'}</p>}
      {item.mode === 'gift' && <p className="field-hint">{item.availability === 'available' ? '可申请领取' : item.availability === 'reserved' ? '待交接' : item.availability === 'gifted' ? '已赠送' : '已下架'}</p>}
      <h3><Link to={`/items/${item.id}`}>{item.title}</Link></h3>
      <p className="item-card-description">{item.description}</p>
      <div className="item-card-bottom"><strong>{item.mode === 'sale' ? `¥${((item.price_cents ?? 0) / 100).toFixed(2)}` : item.mode === 'borrow' ? '免费借还' : '免费转赠'}</strong><span>{item.owner.nickname}</span></div>
      {item.interest_tags.length > 0 && <div className="tag-list">{item.interest_tags.map(tag => <span key={tag}>{tag}</span>)}</div>}
    </div>
  </article>
}
