import { Link, Route, Routes } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './auth/AuthContext'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { ProfilePage } from './pages/ProfilePage'
import { ItemsPage } from './pages/ItemsPage'
import { ItemDetailPage } from './pages/ItemDetailPage'
import { ItemFormPage } from './pages/ItemFormPage'
import { MyItemsPage } from './pages/MyItemsPage'
import { MyTradesPage } from './pages/MyTradesPage'
import { MyBorrowsPage } from './pages/MyBorrowsPage'
import { MessagesPage } from './pages/MessagesPage'
import { ReportsPage } from './pages/ReportsPage'
import { MyGiftsPage } from './pages/MyGiftsPage'

export default function AppRoutes() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
        <Route path="/items" element={<ItemsPage />} />
        <Route path="/items/:id" element={<ItemDetailPage />} />
        <Route path="/items/new" element={<ProtectedRoute><ItemFormPage /></ProtectedRoute>} />
        <Route path="/my-items" element={<ProtectedRoute><MyItemsPage /></ProtectedRoute>} />
        <Route path="/my-trades" element={<ProtectedRoute><MyTradesPage /></ProtectedRoute>} />
        <Route path="/my-borrows" element={<ProtectedRoute><MyBorrowsPage /></ProtectedRoute>} />
        <Route path="/messages" element={<ProtectedRoute><MessagesPage /></ProtectedRoute>} />
        <Route path="/my-reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
        <Route path="/admin/reports" element={<ProtectedRoute><ReportsPage admin /></ProtectedRoute>} />
        <Route path="/my-gifts" element={<ProtectedRoute><MyGiftsPage /></ProtectedRoute>} />
        <Route path="*" element={<main className="auth-loading"><h1>页面不存在</h1><Link to="/">返回首页</Link></main>} />
      </Routes>
    </AuthProvider>
  )
}
