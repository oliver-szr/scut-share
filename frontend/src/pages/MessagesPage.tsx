import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { errorMessage } from '../api/client'
import { conversationsApi } from '../api/conversations'
import type { Conversation, ConversationList, Message } from '../api/conversations'
import { imageUrl } from '../api/items'
import { useAuth } from '../auth/AuthContext'
import { SiteHeader } from '../components/SiteHeader'
import { ReportButton } from '../components/ReportButton'

function mergeMessages(current: Message[], incoming: Message[]): Message[] {
  const rows = new Map(current.map(message => [message.id, message]))
  incoming.forEach(message => rows.set(message.id, message))
  return [...rows.values()].sort((a, b) => a.id - b.id)
}

export function MessagesPage() {
  const { state } = useAuth()
  const [params, setParams] = useSearchParams()
  const rawId = params.get('conversation')
  const selectedId = rawId && /^[1-9]\d*$/.test(rawId) && Number.isSafeInteger(Number(rawId)) ? Number(rawId) : null
  const [list, setList] = useState<ConversationList | null>(null)
  const [page, setPage] = useState(1)
  const [listRevision, setListRevision] = useState(0)
  const [listLoading, setListLoading] = useState(true)
  const [listError, setListError] = useState<string | null>(null)
  const [conversation, setConversation] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)
  const [paused, setPaused] = useState(false)
  const [revision, setRevision] = useState(0)
  const [hasOlder, setHasOlder] = useState(false)
  const [olderBusy, setOlderBusy] = useState(false)
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const selectedRef = useRef(selectedId)
  selectedRef.current = selectedId
  const pausedRef = useRef(false)
  const sendController = useRef<AbortController | null>(null)
  const olderController = useRef<AbortController | null>(null)
  const feed = useRef<HTMLDivElement | null>(null)
  const preserveScroll = useRef(false)

  useEffect(() => {
    const controller = new AbortController()
    setListLoading(true); setListError(null)
    conversationsApi.list(page, controller.signal).then(result => { if (!controller.signal.aborted) setList(result) })
      .catch(failure => { if (!controller.signal.aborted) setListError(errorMessage(failure)) })
      .finally(() => { if (!controller.signal.aborted) setListLoading(false) })
    return () => controller.abort()
  }, [page, listRevision])

  const updatePreview = (message: Message) => {
    setList(current => current && ({ ...current, conversations: current.conversations.map(row => row.id === message.conversation_id
      && (!row.last_message || row.last_message.id <= message.id) ? { ...row, last_message: { ...message, content: message.content.slice(0, 100) }, last_message_at: message.created_at, updated_at: message.created_at } : row)
      .sort((a, b) => b.updated_at.localeCompare(a.updated_at) || b.id - a.id) }))
  }

  useEffect(() => {
    const controller = new AbortController()
    let pollController: AbortController | null = null
    let timer: ReturnType<typeof setTimeout> | undefined
    let disposed = false; let ready = false; let inFlight = false; let cursor = 0
    sendController.current?.abort(); sendController.current = null
    olderController.current?.abort(); olderController.current = null
    preserveScroll.current = false
    setSending(false); setDraft(''); setConversation(null); setMessages([]); setChatError(null); setHasOlder(false); setOlderBusy(false)
    pausedRef.current = false; setPaused(false); setLoading(selectedId !== null)
    const schedule = () => {
      clearTimeout(timer)
      if (!disposed && ready && !pausedRef.current && !document.hidden) timer = setTimeout(() => void poll(), 8000)
    }
    const poll = async () => {
      if (!selectedId || disposed || document.hidden || pausedRef.current || inFlight) return
      inFlight = true; pollController = new AbortController()
      try {
        const result = await conversationsApi.messages(selectedId, { after_id: cursor }, pollController.signal)
        if (!disposed && !pollController.signal.aborted) {
          setMessages(current => mergeMessages(current, result.messages))
          if (result.messages.length) { const last = result.messages[result.messages.length - 1]; cursor = last.id; updatePreview(last) }
        }
      } catch (failure) {
        if (!disposed && !pollController.signal.aborted) { setChatError(errorMessage(failure)); pausedRef.current = true; setPaused(true) }
      } finally { inFlight = false; schedule() }
    }
    const visibility = () => {
      clearTimeout(timer)
      if (document.hidden) pollController?.abort()
      else schedule()
    }
    document.addEventListener('visibilitychange', visibility)
    if (selectedId) {
      Promise.all([conversationsApi.get(selectedId, controller.signal), conversationsApi.messages(selectedId, {}, controller.signal)])
        .then(([details, history]) => {
          if (disposed) return
          setConversation(details); setMessages(history.messages); setHasOlder(history.has_more)
          cursor = history.messages.at(-1)?.id ?? 0; ready = true; schedule()
        }).catch(failure => {
          if (!disposed) { setChatError(errorMessage(failure)); pausedRef.current = true; setPaused(true) }
        }).finally(() => { if (!disposed) setLoading(false) })
    }
    return () => { disposed = true; clearTimeout(timer); controller.abort(); pollController?.abort(); sendController.current?.abort(); olderController.current?.abort(); document.removeEventListener('visibilitychange', visibility) }
  }, [selectedId, revision])

  useEffect(() => {
    if (preserveScroll.current) { preserveScroll.current = false; return }
    if (feed.current) feed.current.scrollTop = feed.current.scrollHeight
  }, [messages])

  const older = async () => {
    if (!selectedId || olderController.current || !messages.length) return
    const id = selectedId; const controller = new AbortController(); olderController.current = controller; setOlderBusy(true)
    try {
      const result = await conversationsApi.messages(id, { before_id: messages[0].id }, controller.signal)
      if (!controller.signal.aborted && selectedRef.current === id) { preserveScroll.current = true; setMessages(current => mergeMessages(current, result.messages)); setHasOlder(result.has_more) }
    } catch (failure) {
      if (!controller.signal.aborted && selectedRef.current === id) { setChatError(errorMessage(failure)); pausedRef.current = true; setPaused(true) }
    } finally { if (olderController.current === controller) { olderController.current = null; setOlderBusy(false) } }
  }

  const send = async () => {
    const content = draft.trim()
    if (!selectedId || !conversation || !content || content.length > 1000 || sendController.current) return
    const id = selectedId; const controller = new AbortController(); sendController.current = controller
    setSending(true); if (!pausedRef.current) setChatError(null)
    try {
      const message = await conversationsApi.send(id, content, controller.signal)
      if (!controller.signal.aborted && selectedRef.current === id) { setMessages(current => mergeMessages(current, [message])); setDraft(''); updatePreview(message) }
      // Advance the polling cursor only from reads, so a sent message cannot skip unseen replies.
    } catch (failure) {
      if (!controller.signal.aborted && selectedRef.current === id) { setChatError(`${errorMessage(failure)} 请重新加载核对消息后再重发。`); pausedRef.current = true; setPaused(true) }
    } finally {
      if (sendController.current === controller) { sendController.current = null; setSending(false) }
    }
  }

  const active = conversation?.id === selectedId ? conversation : null
  return <div className="min-h-screen"><SiteHeader /><main className="page-width messages-page">
    <div className="items-heading"><div><p className="eyebrow">MESSAGES</p><h1>我的消息</h1><p>围绕物品自主沟通，交易与借还仍需在对应记录中确认。</p></div></div>
    {rawId && !selectedId && <p className="form-error" role="alert">会话编号无效。</p>}
    <div className={`messages-shell ${selectedId ? 'conversation-open' : ''}`}>
      <aside className="conversation-sidebar" aria-label="会话列表">
        <div className="conversation-list-heading"><h2>会话</h2><button className="text-button" disabled={listLoading} onClick={() => setListRevision(value => value + 1)}>刷新列表</button></div>
        {listLoading && <p role="status">正在加载会话…</p>}
        {listError && <p className="form-error" role="alert">{listError}</p>}
        {!listLoading && !listError && list?.conversations.length === 0 && <p className="field-hint">暂无会话，从二手商品或已同意的借还记录开始沟通。</p>}
        {list?.conversations.map(row => <button type="button" key={row.id} className={`conversation-entry ${selectedId === row.id ? 'active' : ''}`} aria-pressed={selectedId === row.id} onClick={() => setParams({ conversation: String(row.id) })}>
          {row.item.images[0] && <img src={imageUrl(row.item.images[0].url)} alt="" />}
          <span><strong>{row.other_user.nickname}</strong><span>{row.item.title} · {row.context_type === 'sale_item' ? '二手咨询' : '免费借还'}</span><small>{row.last_message?.content ?? '尚无消息'}</small>{row.last_message_at && <time dateTime={row.last_message_at}>{new Date(row.last_message_at).toLocaleString('zh-CN')}</time>}</span>
        </button>)}
        {list && list.total > list.page_size && <div className="pagination"><button disabled={page === 1 || listLoading} onClick={() => setPage(value => value - 1)}>上一页</button><span>{page}</span><button disabled={page * list.page_size >= list.total || listLoading} onClick={() => setPage(value => value + 1)}>下一页</button></div>}
      </aside>
      <section className="chat-panel" aria-label="聊天内容">
        {selectedId ? <>
          <button className="text-button mobile-conversation-back" onClick={() => setParams({})}>← 返回会话列表</button>
          {loading && <p className="auth-loading" role="status">正在加载消息…</p>}
          {chatError && <div className="form-error" role="alert">{chatError}{paused && <span> 自动更新已暂停。</span>} <button className="text-button" onClick={() => setRevision(value => value + 1)}>重新加载</button></div>}
          {active && !loading && <>
            <header className="chat-heading">{active.item.images[0] && <img src={imageUrl(active.item.images[0].url)} alt="" />}<div><h2>{active.other_user.nickname}</h2><Link to={`/items/${active.item_id}`}>{active.item.title}</Link></div></header>
            <div className="message-feed" ref={feed} aria-label="历史消息">
              {hasOlder && <button className="text-button load-older" disabled={olderBusy} onClick={() => void older()}>{olderBusy ? '正在加载…' : '加载更早消息'}</button>}
              {messages.length === 0 && <p className="field-hint">还没有消息，发送第一句话吧。</p>}
              {messages.map(message => <article className={`message-row ${state.user?.id === message.sender_id ? 'own' : ''}`} key={message.id} aria-label={`消息 ${message.id}`}>
                <span>{state.user?.id === message.sender_id ? '我' : active.other_user.nickname}</span><p>{message.content}</p><time dateTime={message.created_at}>{new Date(message.created_at).toLocaleString('zh-CN')}</time><ReportButton target="message" id={message.id} />
              </article>)}
            </div>
            <form className="message-composer" onSubmit={event => { event.preventDefault(); void send() }}><label htmlFor="message-content">消息内容</label><textarea id="message-content" maxLength={1000} value={draft} disabled={sending} onChange={event => setDraft(event.target.value)} placeholder="输入文字消息，最多 1000 字" /><div><span className="field-hint">{draft.length}/1000 · 仅支持文字</span><button className="form-submit" disabled={sending || !draft.trim()}>{sending ? '正在发送…' : '发送'}</button></div></form>
          </>}
        </> : <div className="empty-state"><h2>选择一个会话开始沟通</h2><p>只有会话双方可以查看和发送消息。</p></div>}
      </section>
    </div>
  </main></div>
}
