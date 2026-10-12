import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { errorMessage } from '../api/client'
import { conversationsApi } from '../api/conversations'
import type { ChatContext } from '../api/conversations'

export function ContactButton({ context, id, label = '联系对方' }: { context: ChatContext; id: number; label?: string }) {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const submitting = useRef(false)
  const contact = async () => {
    if (submitting.current) return
    submitting.current = true; setBusy(true); setError(null)
    try { const conversation = await conversationsApi.start(context, id); navigate(`/messages?conversation=${conversation.id}`) }
    catch (failure) { setError(errorMessage(failure)) }
    finally { submitting.current = false; setBusy(false) }
  }
  return <div className="contact-action"><button className="contact-button" type="button" disabled={busy} onClick={() => void contact()}>{busy ? '正在打开…' : label}</button>{error && <p className="form-error" role="alert">{error}</p>}</div>
}
