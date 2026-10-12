import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export function SiteHeader({ home = false }: { home?: boolean }) {
  const { state, refresh } = useAuth()
  return (
    <header className="site-header">
      <div className="page-width header-inner">
        <Link to="/" className="brand" aria-label="华园易享首页">
          <span className="brand-symbol" aria-hidden="true">享</span>
          <span><strong>华园易享</strong><small>SCUT SHARE</small></span>
        </Link>
        <nav className="header-nav" aria-label="主导航">
          {home && <Link className="home-explore-link" to="/items">探索物品</Link>}
          {home && <a className="home-explore-link" href="#idea">我们的理念</a>}
          {state.status === 'loading' && <span role="status">恢复登录中…</span>}
          {state.status === 'unavailable' && <button className="text-button" onClick={() => void refresh()}>登录状态重试</button>}
          {state.status === 'anonymous' && <><Link to="/login">登录</Link><Link to="/register" className="nav-account">注册</Link></>}
          {state.status === 'authenticated' && <Link to="/profile" className="account-link" aria-label="个人中心">
            <span className="account-name">{state.user.nickname}</span><span>个人中心</span>
          </Link>}
          {state.status === 'authenticated' && <Link className="home-explore-link" to="/my-items">我的发布</Link>}
          {state.status === 'authenticated' && <span className="header-secondary-links"><Link to="/my-trades">我的交易</Link><Link to="/my-borrows">我的借还</Link><Link to="/messages">我的消息</Link><Link to="/my-gifts">我的转赠</Link></span>}
        </nav>
      </div>
    </header>
  )
}
