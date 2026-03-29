import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function ProtectedRoute() {
  const { token, bootstrapped } = useAuth()
  if (bootstrapped === null) return null
  if (!bootstrapped) return <Navigate to="/setup" replace />
  if (!token) return <Navigate to="/login" replace />
  return <Outlet />
}

