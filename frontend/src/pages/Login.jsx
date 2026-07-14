import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { login, getMe } from '../services/auth'
import { TrendingUp } from 'lucide-react'

export default function Login() {
  const navigate    = useNavigate()
  const { loginUser } = useAuth()

  const [form, setForm]       = useState({ email: '', password: '' })
  const [error, setError]     = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
    setError('') // clear error when user starts typing again
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      // step 1 — get the token
      const tokenData = await login(form.email, form.password)

      // step 2 — use the token to fetch the user profile
      // we need this to populate the auth context
      localStorage.setItem('token', tokenData.access_token)
      const userData = await getMe()

      loginUser(tokenData.access_token, userData)
      navigate('/market')
    } catch (err) {
      // show whatever error message the backend sent back
      const msg = err.response?.data?.detail || 'Something went wrong. Try again.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center px-4">
      <div className="w-full max-w-md">

        {/* logo / brand */}
        <div className="flex items-center gap-2 justify-center mb-8">
          <TrendingUp className="text-blue-500" size={28} />
          <span className="text-xl font-semibold text-white">TradeSim</span>
        </div>

        <div className="card">
          <h1 className="text-lg font-semibold text-white mb-1">Welcome back</h1>
          <p className="text-sm text-gray-500 mb-6">Sign in to your paper trading account</p>

          {/* error banner */}
          {error && (
            <div className="mb-4 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Email</label>
              <input
                type="email"
                name="email"
                value={form.email}
                onChange={handleChange}
                placeholder="you@example.com"
                className="input"
                required
              />
            </div>

            <div>
              <label className="block text-xs text-gray-400 mb-1">Password</label>
              <input
                type="password"
                name="password"
                value={form.password}
                onChange={handleChange}
                placeholder="••••••••"
                className="input"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <p className="mt-5 text-center text-sm text-gray-500">
            Don't have an account?{' '}
            <Link to="/register" className="text-blue-400 hover:text-blue-300">
              Create one
            </Link>
          </p>
        </div>

        {/* demo credentials hint — helpful during development */}
        <p className="text-center text-xs text-gray-600 mt-4">
          Demo platform — no real money involved
        </p>
      </div>
    </div>
  )
}
