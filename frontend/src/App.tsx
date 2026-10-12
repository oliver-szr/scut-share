import { ConnectionStatus } from './components/ConnectionStatus'
import { Link } from 'react-router-dom'
import { ShareIllustration } from './components/ShareIllustration'
import { SiteHeader } from './components/SiteHeader'

export default function App() {
  return (
    <div className="min-h-screen">
      <a className="skip-link" href="#main">跳转到主要内容</a>
      <SiteHeader home />

      <main id="main" className="page-width">
        <section className="hero grid items-center gap-2 lg:grid-cols-[1.15fr_1fr]" aria-labelledby="hero-title">
          <div className="hero-copy">
            <p className="eyebrow"><span aria-hidden="true">✳</span> 闲置有新去处，生活多一份可能</p>
            <h1 id="hero-title">让闲置流动，<br />让<span>校园互助</span>发生。</h1>
            <p className="hero-description">一本读完的书，一件偶尔才用的物品。<br className="hidden sm:block" />在华园，为它找到下一位需要的同学。</p>
            <div className="hero-actions"><Link className="primary-link" to="/items">浏览物品 <span aria-hidden="true">↗</span></Link><Link className="secondary-link" to="/items/new">发布物品 <span aria-hidden="true">＋</span></Link></div>
            <p className="hero-note">为华南理工大学学生设计的二手交易与免费借还平台</p>
          </div>
          <div className="illustration-wrap">
            <span className="illustration-label">一份闲置 · 一次新生</span>
            <ShareIllustration />
            <span className="illustration-caption">SHARE A LITTLE. CONNECT A LOT.</span>
          </div>
        </section>

        <section id="explore" className="explore-section" aria-labelledby="explore-title">
          <div className="section-heading flex flex-wrap items-end justify-between gap-3">
            <div><p className="eyebrow">TWO WAYS TO SHARE</p><h2 id="explore-title">两种方式，一样的善意</h2></div>
            <p>让物品被珍惜，也让需要被看见。</p>
          </div>
          <div className="grid gap-5 md:grid-cols-2">
            <article className="path-card trade-card">
              <div className="flex items-start justify-between gap-4"><span className="path-icon" aria-hidden="true">↗</span><span className="development-badge">已开放</span></div>
              <p className="path-label">PASS IT ON</p><h3>二手交易</h3>
              <p className="path-description">把用不上的闲置，交给正好需要的同学。<br />自由协商，约好时间，校园里见。</p>
              <div className="path-bottom"><Link to="/my-trades">我的交易</Link><Link role="button" aria-label="二手交易 · 浏览二手出售" to="/items?mode=sale">浏览二手出售 <span aria-hidden="true">→</span></Link></div>
            </article>
            <article className="path-card borrow-card">
              <div className="flex items-start justify-between gap-4"><span className="path-icon" aria-hidden="true">⇄</span><span className="development-badge">已开放</span></div>
              <p className="path-label">SHARE & RETURN</p><h3>免费借还</h3>
              <p className="path-description">偶尔需要的东西，不一定要买下来。<br />免费借用，协商交接，用完如约归还。</p>
              <div className="path-bottom"><Link to="/my-borrows">我的借还</Link><Link role="button" aria-label="免费借还 · 浏览免费借还" to="/items?mode=borrow">浏览免费借还 <span aria-hidden="true">→</span></Link></div>
            </article>
          </div>
        </section>

        <section id="idea" className="idea-section grid gap-7 md:grid-cols-[1fr_1.5fr]" aria-labelledby="idea-title">
          <div><p className="eyebrow">MADE FOR OUR CAMPUS</p><h2 id="idea-title">互助，从身边开始。</h2><p className="idea-intro">从班级熟人圈出发，<br />让每一次分享都轻松而真诚。</p></div>
          <div className="grid gap-6 sm:grid-cols-3">
            <div className="idea-item"><span aria-hidden="true">01 /</span><h3>物尽其用</h3><p>延长物品的使用时间，让闲置回到生活里。</p></div>
            <div className="idea-item"><span aria-hidden="true">02 /</span><h3>平等分享</h3><p>交易与借还并行，按自己的需要选择。</p></div>
            <div className="idea-item"><span aria-hidden="true">03 /</span><h3>相互尊重</h3><p>自主沟通，认真约定，让校园互助自然发生。</p></div>
          </div>
        </section>

        <aside className="project-notice flex flex-wrap items-center justify-between gap-4" aria-label="项目开发进度">
          <p><strong>校园试点 · 逐步完善中</strong><span>注册、登录、物品发布、二手交易、免费借还与站内文字聊天已开放，举报申诉、免费转赠与挂牌价格参考也已开放。</span><Link to="/messages">我的消息 →</Link><Link to="/items?mode=gift">浏览免费转赠 →</Link></p>
          <ConnectionStatus />
        </aside>
      </main>
      <footer className="page-width site-footer flex flex-wrap items-center justify-between gap-3">
        <p>华园易享 <span>SCUT Share</span></p><p>创新思维与实践 · 学生课程项目</p><p>五山 · 大学城 · 广州国际校区</p>
      </footer>
    </div>
  )
}
