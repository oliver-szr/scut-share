import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { errorMessage } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { AuthLayout } from '../components/AuthLayout'

export function LoginPage() {
  const { login, state } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [studentNo, setStudentNo] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (busy) return
    if (!/^[A-Za-z0-9_-]{3,32}$/.test(studentNo.trim()) || !password || Array.from(password).length > 128) {
      setError('请填写有效的学号和密码。')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await login({ student_no: studentNo.trim(), password })
      navigate('/', { replace: true })
    } catch (failure) { setError(errorMessage(failure)) }
    finally { setBusy(false) }
  }

  const registered = typeof location.state === 'object' && location.state !== null && location.state.registered === true
  return (
    <AuthLayout title="欢迎回来" subtitle="登录账号，延续身边的分享与互助。">
      {registered && <p className="form-success" role="status">注册成功，请使用学号和密码登录。</p>}
      {state.message && <p className="form-error" role="alert">{state.message}</p>}
      <form className="auth-form" onSubmit={submit} noValidate>
        <div className="form-field"><label htmlFor="login-student-no">学号</label><input id="login-student-no" autoComplete="username" required value={studentNo} onChange={event => setStudentNo(event.target.value)} placeholder="你的登录账号" /></div>
        <div className="form-field"><label htmlFor="login-password">密码</label><input id="login-password" type="password" autoComplete="current-password" required value={password} onChange={event => setPassword(event.target.value)} placeholder="请输入密码" /></div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="form-submit" disabled={busy} type="submit">{busy ? '正在登录…' : '登录'}</button>
      </form>
      <p className="auth-switch">还没有账号？<Link to="/register">前往注册</Link></p>
    </AuthLayout>
  )
}
