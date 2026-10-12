import { apiClient } from './client'
import type { ItemImage, ItemOwner } from './items'

export interface Message { id: number; conversation_id: number; sender_id: number; content: string; created_at: string }
export interface Conversation {
  id: number; context_type: 'sale_item' | 'borrow_request'; item_id: number; borrow_request_id: number | null
  other_user: ItemOwner; item: { id: number; title: string; images: ItemImage[] }
  last_message: Message | null; last_message_at: string | null; created_at: string; updated_at: string
}
export interface ConversationList { conversations: Conversation[]; total: number; page: number; page_size: number }
export interface MessageList { messages: Message[]; has_more: boolean }
export type ChatContext = 'item' | 'trade' | 'borrow'

function parseConversation(data: unknown): Conversation {
  if (typeof data !== 'object' || data === null || !('id' in data) || typeof data.id !== 'number' || !('other_user' in data)) throw new Error('Invalid conversation response')
  return data as Conversation
}
function parseMessage(data: unknown): Message {
  if (typeof data !== 'object' || data === null || !('id' in data) || typeof data.id !== 'number' || !('content' in data) || typeof data.content !== 'string') throw new Error('Invalid message response')
  return data as Message
}

export const conversationsApi = {
  start: async (context: ChatContext, id: number) => parseConversation(await apiClient.post(
    context === 'item' ? `/items/${id}/conversations` : context === 'trade' ? `/trades/${id}/conversation` : `/borrows/${id}/conversation`, {},
  )),
  list: async (page = 1, signal?: AbortSignal): Promise<ConversationList> => {
    const data = await apiClient.get(`/conversations?page=${page}&page_size=20`, signal)
    if (typeof data !== 'object' || data === null || !('conversations' in data) || !Array.isArray(data.conversations)) throw new Error('Invalid conversation list response')
    return { ...(data as ConversationList), conversations: data.conversations.map(parseConversation) }
  },
  get: async (id: number, signal?: AbortSignal) => parseConversation(await apiClient.get(`/conversations/${id}`, signal)),
  messages: async (id: number, cursor: { before_id?: number; after_id?: number } = {}, signal?: AbortSignal): Promise<MessageList> => {
    const query = new URLSearchParams({ limit: '50' })
    if (cursor.before_id !== undefined) query.set('before_id', String(cursor.before_id))
    if (cursor.after_id !== undefined) query.set('after_id', String(cursor.after_id))
    const data = await apiClient.get(`/conversations/${id}/messages?${query}`, signal)
    if (typeof data !== 'object' || data === null || !('messages' in data) || !Array.isArray(data.messages)) throw new Error('Invalid message list response')
    return { ...(data as MessageList), messages: data.messages.map(parseMessage) }
  },
  send: async (id: number, content: string, signal?: AbortSignal) => parseMessage(await apiClient.post(`/conversations/${id}/messages`, { content }, signal)),
}
