import { useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { errorMessage } from '../api/client'
import { reportsApi } from '../api/reports'
import type { ReportTarget } from '../api/reports'

export function ReportButton({ target, id }: { target: ReportTarget; id: number }) {
  const fieldId = useId()
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('信息虚假或违规')
  const [description, setDescription] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState<number | null>(null)
  const submitting = useRef(false)
  const submit = async () => {
    if (submitting.current || !description.trim()) return
    submitting.current = true; setBusy(true); setError(null)
    try { const report = await reportsApi.create(target, id, reason, description.trim()); setSubmitted(report.id); setOpen(false) }
    catch (failure) { setError(errorMessage(failure)) }
    finally { submitting.current = false; setBusy(false) }
  }
  return <div className="report-action">
    {submitted ? <p className="field-hint" role="status">举报已提交。<Link to={`/my-reports?report=${submitted}`}>查看处理进度</Link></p>
      : <button className="text-button" type="button" onClick={() => setOpen(value => !value)}>举报</button>}
    {open && <form className="report-form" onSubmit={event => { event.preventDefault(); void submit() }}>
      <label htmlFor={`${fieldId}-reason`}>举报原因</label><select id={`${fieldId}-reason`} value={reason} disabled={busy} onChange={event => setReason(event.target.value)}>{['信息虚假或违规', '欺诈或描述不符', '逾期、损坏或未归还', '不当沟通', '其他'].map(value => <option key={value}>{value}</option>)}</select>
      <label htmlFor={`${fieldId}-description`}>详细描述</label><textarea id={`${fieldId}-description`} required maxLength={2000} value={description} disabled={busy} onChange={event => setDescription(event.target.value)} />
      {target === 'message' && <p className="field-hint">只提交选中这一条消息的证据，不提交全部聊天记录。</p>}
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="contact-button" disabled={busy || !description.trim()}>{busy ? '正在提交…' : '提交举报'}</button>
      <button className="text-button" type="button" disabled={busy} onClick={() => setOpen(false)}>取消</button>
    </form>}
  </div>
}
