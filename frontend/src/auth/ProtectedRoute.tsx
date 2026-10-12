import type { ReactNode } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from './AuthContext'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { state, refresh } = useAuth()
  if (state.status === 'loading') return <p className="auth-loading" role="status">正在恢复登录状态…</p>
  if (state.status === 'anonymous') return <Navigate to="/login" replace />
  if (state.status === 'unavailable') return (
    <main className="auth-loading"><p role="alert">{state.message}</p>
      <button className="text-button" type="button" onClick={() => void refresh()}>重新连接</button>
      <Link to="/">返回首页</Link>
    </main>
  )
  return children
}
