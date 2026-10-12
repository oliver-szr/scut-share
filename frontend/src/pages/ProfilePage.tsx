import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { errorMessage } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { AuthLayout } from '../components/AuthLayout'

export function ProfilePage() {
  const { state, logout } = useAuth()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  if (state.status !== 'authenticated') return null

  const signOut = async () => {
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      await logout()
      navigate('/login', { replace: true })
    } catch (failure) { setError(errorMessage(failure)) }
    finally { setBusy(false) }
  }

  return (
    <AuthLayout title="个人中心" subtitle="你的账号信息，仅对你自己可见。">
      <dl className="profile-details">
        <div><dt>昵称</dt><dd>{state.user.nickname}</dd></div>
        <div><dt>所属校区</dt><dd>{state.user.campus}</dd></div>
        <div><dt>学号（已脱敏）</dt><dd>{state.user.student_no_masked}</dd></div>
      </dl>
      <p className="field-hint">学号属于内部账号信息，公开资料中不会展示。</p>
      <Link className="primary-link" to="/messages">我的消息 →</Link>
      <Link className="primary-link" to="/my-reports">我的举报与申诉 →</Link>
      <Link className="primary-link" to="/my-gifts">我的转赠 →</Link>
      {state.user.is_admin && <Link className="primary-link" to="/admin/reports">举报管理 →</Link>}
      <div className="owner-actions profile-links"><Link className="primary-link" to="/my-trades">我的交易 →</Link><Link className="primary-link" to="/my-borrows">我的借还 →</Link><Link className="primary-link" to="/my-items">我的发布 →</Link></div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="form-submit signout-button" type="button" disabled={busy} onClick={() => void signOut()}>{busy ? '正在退出…' : '退出登录'}</button>
      <p className="profile-limit">资料修改、头像上传和密码修改尚未开放。</p>
    </AuthLayout>
  )
}
