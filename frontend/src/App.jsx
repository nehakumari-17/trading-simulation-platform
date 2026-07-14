import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'

import Login     from './pages/Login'
import Register  from './pages/Register'
import Layout    from './components/Layout'
import Market    from './pages/Market'
import Portfolio from './pages/Portfolio'
import Orders    from './pages/Orders'
import Strategy  from './pages/Strategy'
import Risk      from './pages/Risk'

function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* public */}
        <Route path="/login"    element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* protected — user must be logged in to access these */}
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/"          element={<Navigate to="/market" replace />} />
            <Route path="/market"    element={<Market />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/orders"    element={<Orders />} />
            <Route path="/strategy"  element={<Strategy />} />
            <Route path="/risk"      element={<Risk />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </AuthProvider>
  )
}

export default App
