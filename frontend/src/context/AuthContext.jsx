import { createContext, useContext, useState, useEffect } from 'react'
import { getMe } from '../services/auth'

// this context holds the logged-in user across the whole app
// any component can call useAuth() to get the user or logout function
const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null)
  const [loading, setLoading] = useState(true)  // true while we check existing session

  // on first load — if there's a token in localStorage, try to restore the session
  // this keeps the user logged in after a page refresh
  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      setLoading(false)
      return
    }

    getMe()
      .then((u) => setUser(u))
      .catch(() => {
        // token is stale or invalid — clear it
        localStorage.removeItem('token')
        localStorage.removeItem('user')
      })
      .finally(() => setLoading(false))
  }, [])

  // called after a successful login
  const loginUser = (token, userData) => {
    localStorage.setItem('token', token)
    setUser(userData)
  }

  // clear everything and send to login
  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
    window.location.href = '/login'
  }

  if (loading) {
    // show a blank screen while we figure out auth state
    // could replace with a spinner later
    return (
      <div className="flex items-center justify-center h-screen bg-[#0f0f0f]">
        <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <AuthContext.Provider value={{ user, loginUser, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// shorthand hook — import this instead of useContext(AuthContext)
export const useAuth = () => useContext(AuthContext)
