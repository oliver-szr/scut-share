import { useNavigate } from 'react-router-dom'
import { ItemForm } from '../components/ItemForm'
import { SiteHeader } from '../components/SiteHeader'

export function ItemFormPage() { const navigate = useNavigate(); return <div className="min-h-screen"><SiteHeader /><main className="page-width narrow-page"><section className="auth-panel"><p className="eyebrow">SCUT SHARE · PUBLISH</p><h1>发布物品</h1><p className="auth-subtitle">填写真实信息，让同学更容易找到它。</p><ItemForm onSuccess={item => navigate(`/items/${item.id}`, { replace: true })} /></section></main></div> }
