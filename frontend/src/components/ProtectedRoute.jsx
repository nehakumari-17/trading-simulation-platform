import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

// wraps any route that requires login
// if there's no user, redirect to /login
// Outlet renders whatever child route matched
export default function ProtectedRoute() {
  const { user } = useAuth()

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
