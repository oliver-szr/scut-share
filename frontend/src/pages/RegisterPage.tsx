import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi, CAMPUSES } from '../api/auth'
import type { Campus, RegistrationInput } from '../api/auth'
import { errorMessage } from '../api/client'
import { validateRegistration } from '../auth/validation'
import { AuthLayout } from '../components/AuthLayout'

export function RegisterPage() {
  const navigate = useNavigate()
  const [input, setInput] = useState<RegistrationInput>({ nickname: '', student_no: '', password: '', campus: '' })
  const [errors, setErrors] = useState<Partial<Record<keyof RegistrationInput, string>>>({})
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (busy) return
    const validation = validateRegistration(input)
    setErrors(validation)
    setError(null)
    if (Object.keys(validation).length) return
    setBusy(true)
    try {
      await authApi.register({ ...input, nickname: input.nickname.trim(), student_no: input.student_no.trim() })
      navigate('/login', { replace: true, state: { registered: true } })
    } catch (failure) {
      setError(errorMessage(failure))
    } finally { setBusy(false) }
  }

  return (
    <AuthLayout title="加入华园易享" subtitle="创建账号，为闲置找到新去处。">
      <form className="auth-form" onSubmit={submit} noValidate>
        <div className="form-field"><label htmlFor="nickname">昵称</label>
          <input id="nickname" autoComplete="nickname" required value={input.nickname} aria-invalid={Boolean(errors.nickname)} aria-describedby={errors.nickname ? 'nickname-error' : undefined} onChange={event => setInput({ ...input, nickname: event.target.value })} placeholder="2～30 个字符，可与他人相同" />
          {errors.nickname && <p id="nickname-error" className="field-error">{errors.nickname}</p>}
        </div>
        <div className="form-field"><label htmlFor="student-no">学号</label>
          <input id="student-no" autoComplete="username" required value={input.student_no} aria-invalid={Boolean(errors.student_no)} aria-describedby="student-note student-error" onChange={event => setInput({ ...input, student_no: event.target.value })} placeholder="你的登录账号" />
          <p id="student-note" className="field-hint">自行填写，仅作为内部账号信息，区分字母大小写。</p>
          {errors.student_no && <p id="student-error" className="field-error">{errors.student_no}</p>}
        </div>
        <div className="form-field"><label htmlFor="password">密码</label>
          <input id="password" type="password" autoComplete="new-password" required value={input.password} aria-invalid={Boolean(errors.password)} aria-describedby={errors.password ? 'password-error' : undefined} onChange={event => setInput({ ...input, password: event.target.value })} placeholder="8～128 个字符" />
          {errors.password && <p id="password-error" className="field-error">{errors.password}</p>}
        </div>
        <div className="form-field"><label htmlFor="campus">所属校区</label>
          <select id="campus" required value={input.campus} aria-invalid={Boolean(errors.campus)} aria-describedby={errors.campus ? 'campus-error' : undefined} onChange={event => setInput({ ...input, campus: event.target.value as Campus | '' })}>
            <option value="" disabled>请选择校区</option>{CAMPUSES.map(campus => <option key={campus} value={campus}>{campus}</option>)}
          </select>{errors.campus && <p id="campus-error" className="field-error">{errors.campus}</p>}
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="form-submit" disabled={busy} type="submit">{busy ? '正在注册…' : '注册账号'}</button>
      </form>
      <p className="auth-switch">已有账号？<Link to="/login">前往登录</Link></p>
    </AuthLayout>
  )
}
