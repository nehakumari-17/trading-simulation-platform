import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getSummary } from '../services/portfolio'
import { User } from 'lucide-react'

// map route paths to readable page titles
const PAGE_TITLES = {
  '/market':    'Market',
  '/portfolio': 'Portfolio',
  '/orders':    'Orders',
  '/strategy':  'Strategy',
  '/risk':      'Risk',
}

export default function Topbar() {
  const { user }      = useAuth()
  const location      = useLocation()
  const [summary, setSummary] = useState(null)

  const pageTitle = PAGE_TITLES[location.pathname] || 'Dashboard'

  // grab the portfolio summary to show total value in the topbar
  useEffect(() => {
    getSummary()
      .then(setSummary)
      .catch(() => {}) // silently fail — topbar shouldn't crash the page
  }, [location.pathname]) // refresh numbers when user navigates

  // format a number as Indian rupees
  const fmt = (n) =>
    n != null
      ? new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n)
      : '—'

  const pnlColor = summary?.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'

  return (
    <header className="h-14 bg-[#1a1a1a] border-b border-[#2a2a2a] px-5
                        flex items-center justify-between shrink-0">

      {/* left — page title */}
      <h1 className="text-sm font-semibold text-white">{pageTitle}</h1>

      {/* right — portfolio snapshot + user name */}
      <div className="flex items-center gap-6">

        {summary && (
          <div className="flex items-center gap-5 text-xs">
            <div className="text-right">
              <p className="text-gray-500">Portfolio Value</p>
              <p className="text-white font-medium">{fmt(summary.total_value)}</p>
            </div>
            <div className="text-right">
              <p className="text-gray-500">Total P&amp;L</p>
              <p className={`font-medium ${pnlColor}`}>
                {summary.total_pnl >= 0 ? '+' : ''}{fmt(summary.total_pnl)}
              </p>
            </div>
            <div className="text-right">
              <p className="text-gray-500">Cash</p>
              <p className="text-white font-medium">{fmt(summary.cash_balance)}</p>
            </div>
          </div>
        )}

        {/* user badge */}
        <div className="flex items-center gap-2 pl-4 border-l border-[#2a2a2a]">
          <div className="w-7 h-7 rounded-full bg-blue-600/30 flex items-center justify-center">
            <User size={13} className="text-blue-400" />
          </div>
          <span className="text-xs text-gray-300">{user?.username}</span>
        </div>

      </div>
    </header>
  )
}
