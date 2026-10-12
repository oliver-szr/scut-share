import { useRef, useState } from 'react'
import { errorMessage } from '../api/client'
import { borrowsApi } from '../api/borrows'

export function BorrowRequestForm({ itemId, onSuccess }: { itemId: number; onSuccess: () => void }) {
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const submitting = useRef(false)
  const submit = async () => {
    if (submitting.current) return
    setError(null)
    const startTime = new Date(start); const endTime = new Date(end)
    if (!Number.isFinite(startTime.getTime()) || !Number.isFinite(endTime.getTime()) || endTime <= startTime) {
      setError('请填写有效时间，预计归还时间必须晚于预计开始时间。'); return
    }
    submitting.current = true; setBusy(true)
    try {
      await borrowsApi.create(itemId, { requested_start_at: startTime.toISOString(), expected_return_at: endTime.toISOString(), note: note.trim() || null })
      onSuccess()
    } catch (failure) { setError(errorMessage(failure)) }
    finally { submitting.current = false; setBusy(false) }
  }
  return <form className="item-form" onSubmit={event => { event.preventDefault(); void submit() }}>
    <div className="form-field"><label htmlFor="borrow-start">预计开始时间</label><input id="borrow-start" type="datetime-local" required value={start} disabled={busy} onChange={event => setStart(event.target.value)} /></div>
    <div className="form-field"><label htmlFor="borrow-end">预计归还时间</label><input id="borrow-end" type="datetime-local" required value={end} disabled={busy} onChange={event => setEnd(event.target.value)} /></div>
    <div className="form-field"><label htmlFor="borrow-note">申请备注（选填）</label><textarea id="borrow-note" maxLength={300} value={note} disabled={busy} onChange={event => setNote(event.target.value)} /></div>
    <p className="field-hint">按你的本地时间填写。借还完全免费，不收取租金、押金或手续费；交接由双方线下协商。</p>
    {error && <p className="form-error" role="alert">{error}</p>}
    <button className="form-submit" disabled={busy}>{busy ? '正在提交…' : '提交借用申请'}</button>
  </form>
}
