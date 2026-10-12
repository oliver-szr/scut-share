import { useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { CAMPUSES, CATEGORIES, INTEREST_TAGS, itemsApi } from '../api/items'
import type { Item, ItemInput, ItemMode } from '../api/items'
import { errorMessage } from '../api/client'

export function ItemForm({ initial, onSuccess }: { initial?: Item; onSuccess: (item: Item) => void }) {
  const [savedItem, setSavedItem] = useState<Item | undefined>(initial)
  const uploadedFiles = useRef(new Set<File>())
  const [input, setInput] = useState<ItemInput>({
    title: initial?.title ?? '', description: initial?.description ?? '', category: initial?.category ?? CATEGORIES[0],
    mode: initial?.mode ?? 'sale', campus: initial?.campus ?? CAMPUSES[0], price_cents: initial?.price_cents ?? null,
    borrow_note: initial?.borrow_note ?? null, interest_tags: (initial?.interest_tags ?? []) as ItemInput['interest_tags'],
  })
  const [files, setFiles] = useState<File[]>([])
  const [tooManyFiles, setTooManyFiles] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const change = (key: keyof ItemInput, value: unknown) => setInput(previous => ({ ...previous, [key]: value }))
  const selectMode = (mode: ItemMode) => setInput(previous => ({ ...previous, mode, price_cents: mode !== 'sale' ? null : previous.price_cents, borrow_note: mode !== 'borrow' ? null : previous.borrow_note }))
  const toggleTag = (tag: ItemInput['interest_tags'][number]) => setInput(previous => ({ ...previous, interest_tags: previous.interest_tags.includes(tag) ? previous.interest_tags.filter(value => value !== tag) : [...previous.interest_tags, tag] }))
  const chooseFiles = (event: ChangeEvent<HTMLInputElement>) => { const selected = Array.from(event.target.files ?? []); setTooManyFiles(selected.length > 3); setFiles(selected.slice(0, 3)); if (selected.length > 3) setError('最多选择 3 张图片。') }
  const submit = async (event: FormEvent) => {
    event.preventDefault(); if (busy) return; setError(null)
    if (input.title.trim().length < 2 || input.description.trim().length < 1) { setError('请填写物品名称和描述。'); return }
    if (input.mode === 'sale' && (!input.price_cents || input.price_cents <= 0)) { setError('二手出售物品请输入大于 0 的售价。'); return }
    if (input.mode === 'borrow' && !input.borrow_note?.trim()) { setError('请填写借用说明。'); return }
    if (tooManyFiles) { setError('最多选择 3 张图片。'); return }
    if (!savedItem && files.length > 3) { setError('最多选择 3 张图片。'); return }
    setBusy(true)
    try {
      for (const file of files) { if (file.size > 5 * 1024 * 1024) { setError('单张图片不能超过 5MB。'); setBusy(false); return } }
      let item: Item
      if (savedItem) item = await itemsApi.update(savedItem.id, input)
      else { item = await itemsApi.create(input); setSavedItem(item) }
      for (const file of files) {
        if (uploadedFiles.current.has(file)) continue
        item = await itemsApi.upload(item.id, file)
        uploadedFiles.current.add(file)
        setSavedItem(item)
      }
      onSuccess(item)
    } catch (failure) { setError(errorMessage(failure)) } finally { setBusy(false) }
  }
  return <form className="item-form" onSubmit={submit}>
    <div className="mode-toggle item-modes" role="group" aria-label="物品流通方式"><button type="button" disabled={busy} className={input.mode === 'sale' ? 'active' : ''} onClick={() => selectMode('sale')}>二手出售</button><button type="button" disabled={busy} className={input.mode === 'borrow' ? 'active' : ''} onClick={() => selectMode('borrow')}>免费借还</button><button type="button" disabled={busy} className={input.mode === 'gift' ? 'active' : ''} onClick={() => selectMode('gift')}>免费转赠</button></div>
    <div className="form-field"><label htmlFor="item-title">物品名称</label><input id="item-title" value={input.title} onChange={e => change('title', e.target.value)} maxLength={100} required /></div>
    <div className="form-field"><label htmlFor="item-category">分类</label><select id="item-category" value={input.category} onChange={e => change('category', e.target.value)}>{CATEGORIES.map(value => <option key={value}>{value}</option>)}</select></div>
    <div className="form-field"><label htmlFor="item-campus">所属校区</label><select id="item-campus" value={input.campus} onChange={e => change('campus', e.target.value)}>{CAMPUSES.map(value => <option key={value}>{value}</option>)}</select></div>
    <div className="form-field"><label htmlFor="item-description">物品描述</label><textarea id="item-description" value={input.description} onChange={e => change('description', e.target.value)} maxLength={4000} required /></div>
    {input.mode === 'sale' ? <div className="form-field"><label htmlFor="item-price">售价（元）</label><input id="item-price" type="number" min="0.01" step="0.01" value={input.price_cents ? input.price_cents / 100 : ''} onChange={e => change('price_cents', e.target.value ? Math.round(Number(e.target.value) * 100) : null)} required /></div> : input.mode === 'borrow' ? <div className="form-field"><label htmlFor="item-borrow-note">借用说明</label><textarea id="item-borrow-note" value={input.borrow_note ?? ''} onChange={e => change('borrow_note', e.target.value)} maxLength={1000} required /></div> : <p className="field-hint">免费转赠不收取售价、租金或押金。</p>}
    <div className="form-field"><label htmlFor="item-images">图片（最多 3 张，每张不超过 5MB）</label><input id="item-images" type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={chooseFiles} /><p className="field-hint">{files.length ? `已选择 ${files.length} 张` : '可稍后继续补充图片。'}</p></div>
    <fieldset className="tag-field"><legend>兴趣标签</legend><div className="tag-options">{INTEREST_TAGS.map(tag => <label key={tag}><input type="checkbox" checked={input.interest_tags.includes(tag)} onChange={() => toggleTag(tag)} />{tag}</label>)}</div></fieldset>
    {error && <p className="form-error" role="alert">{error}</p>}<button className="form-submit" disabled={busy}>{busy ? '正在保存…' : initial ? '保存修改' : '发布物品'}</button>
  </form>
}
