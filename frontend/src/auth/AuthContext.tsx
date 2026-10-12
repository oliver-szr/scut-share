import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { authApi } from '../api/auth'
import type { CurrentUser, LoginInput } from '../api/auth'
import { ApiError, apiClient, errorMessage } from '../api/client'

type AuthState =
  | { status: 'authenticated'; user: CurrentUser; message: null }
  | { status: 'loading' | 'anonymous' | 'unavailable'; user: null; message: string | null }

interface AuthContextValue {
  state: AuthState
  login: (payload: LoginInput) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: 'loading', user: null, message: null })
  const sequence = useRef(0)
  const restoration = useRef<AbortController | null>(null)

  const refresh = useCallback(async () => {
    restoration.current?.abort()
    const controller = new AbortController()
    restoration.current = controller
    const version = ++sequence.current
    setState({ status: 'loading', user: null, message: null })
    try {
      const user = await authApi.me(controller.signal)
      if (version === sequence.current) setState({ status: 'authenticated', user, message: null })
    } catch (error) {
      if (controller.signal.aborted || version !== sequence.current) return
      if (error instanceof ApiError && error.status === 401) {
        setState(previous => ({ status: 'anonymous', user: null, message: previous.message }))
      } else {
        setState({ status: 'unavailable', user: null, message: errorMessage(error) })
      }
    }
  }, [])

  useEffect(() => {
    const unsubscribe = apiClient.onUnauthorized(() => {
      setState(previous => ({
        status: 'anonymous', user: null,
        message: previous.status === 'authenticated' ? '登录已过期，请重新登录。' : previous.message,
      }))
    })
    void refresh()
    return () => {
      unsubscribe()
      sequence.current++
      restoration.current?.abort()
    }
  }, [refresh])

  const login = async (payload: LoginInput) => {
    restoration.current?.abort()
    const version = ++sequence.current
    const user = await authApi.login(payload)
    if (version === sequence.current) setState({ status: 'authenticated', user, message: null })
  }

  const logout = async () => {
    await authApi.logout()
    sequence.current++
    restoration.current?.abort()
    setState({ status: 'anonymous', user: null, message: null })
  }

  return <AuthContext.Provider value={{ state, login, logout, refresh }}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth requires AuthProvider')
  return context
}
