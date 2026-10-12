import { useEffect, useState } from 'react'
import { getHealth } from '../api/health'

type ConnectionState = 'loading' | 'connected' | 'failed'

export function ConnectionStatus() {
  const [state, setState] = useState<ConnectionState>('loading')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    getHealth(controller.signal)
      .then(() => {
        if (!controller.signal.aborted) setState('connected')
      })
      .catch(() => {
        if (!controller.signal.aborted) setState('failed')
      })
    return () => controller.abort()
  }, [attempt])

  const text = {
    loading: '正在连接后端…',
    connected: '后端已连接',
    failed: '暂时无法连接后端',
  }[state]

  return (
    <div className="connection" data-state={state}>
      <span className="status-dot" aria-hidden="true" />
      <span role="status" aria-live="polite">{text}</span>
      {state === 'failed' && (
        <>
          <span className="connection-hint">请检查本地服务</span>
          <button type="button" onClick={() => {
            setState('loading')
            setAttempt((value) => value + 1)
          }}>重试</button>
        </>
      )}
    </div>
  )
}
