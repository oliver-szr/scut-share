import type { ReactNode } from 'react'
import { SiteHeader } from './SiteHeader'
import { ShareIllustration } from './ShareIllustration'

export function AuthLayout({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main className="page-width auth-shell">
        <aside className="auth-story" aria-label="校园互助理念">
          <p className="eyebrow">A LITTLE SHARE, A NEW CONNECTION</p>
          <h2>校园生活，<br />从一次分享开始。</h2>
          <p>把闲置交给需要的同学，<br />也为彼此留一份善意。</p>
          <ShareIllustration />
        </aside>
        <section className="auth-panel" aria-labelledby="auth-title">
          <p className="eyebrow">SCUT SHARE · 华园易享</p>
          <h1 id="auth-title">{title}</h1><p className="auth-subtitle">{subtitle}</p>
          {children}
          <p className="identity-note">学号由用户自行填写，不代表已完成官方校园身份认证。</p>
        </section>
      </main>
    </div>
  )
}
