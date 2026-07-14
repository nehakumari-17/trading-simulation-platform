import { useState, useEffect } from 'react'
import { getPositions, getTrades, getPerformance, getSummary } from '../services/portfolio'
import { TrendingUp, TrendingDown, Wallet, BarChart2, RefreshCw } from 'lucide-react'

// helper — format as Indian rupees
const inr = (n) =>
  n != null
    ? new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(n)
    : '—'

// small colored number — green if positive, red if negative
const PnlText = ({ value }) => {
  const color = value >= 0 ? 'text-green-400' : 'text-red-400'
  const sign  = value >= 0 ? '+' : ''
  return <span className={color}>{sign}{inr(value)}</span>
}

export default function Portfolio() {
  const [summary,     setSummary]     = useState(null)
  const [positions,   setPositions]   = useState([])
  const [trades,      setTrades]      = useState([])
  const [performance, setPerformance] = useState(null)
  const [tab,         setTab]         = useState('positions') // 'positions' | 'trades'
  const [loading,     setLoading]     = useState(true)

  const loadAll = () => {
    setLoading(true)
    Promise.all([
      getSummary(),
      getPositions(),
      getTrades(),
      getPerformance(),
    ])
      .then(([s, p, t, perf]) => {
        setSummary(s)
        setPositions(p)
        setTrades(t)
        setPerformance(perf)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(loadAll, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-4 max-w-6xl">

      {/* ── top stat cards ───────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          label="Portfolio Value"
          value={inr(summary?.total_value)}
          icon={<Wallet size={16} className="text-blue-400" />}
        />
        <StatCard
          label="Cash Balance"
          value={inr(summary?.cash_balance)}
          icon={<Wallet size={16} className="text-gray-400" />}
        />
        <StatCard
          label="Unrealized P&L"
          value={<PnlText value={summary?.unrealized_pnl ?? 0} />}
          icon={<TrendingUp size={16} className="text-green-400" />}
        />
        <StatCard
          label="Realized P&L"
          value={<PnlText value={summary?.realized_pnl ?? 0} />}
          icon={<TrendingDown size={16} className="text-purple-400" />}
        />
      </div>

      {/* ── performance metrics ───────────────────────────── */}
      {performance && performance.total_trades > 0 && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <BarChart2 size={15} className="text-blue-400" />
            Performance Metrics
          </h3>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
            {[
              { label: 'Total Trades',  value: performance.total_trades },
              { label: 'Win Rate',      value: `${performance.win_rate}%` },
              { label: 'Total Return',  value: inr(performance.total_return) },
              { label: 'Profit Factor', value: performance.profit_factor?.toFixed(2) },
              { label: 'Sharpe Ratio',  value: performance.sharpe_ratio?.toFixed(2) },
              { label: 'Max Drawdown',  value: inr(performance.max_drawdown) },
            ].map(({ label, value }) => (
              <div key={label}>
                <p className="text-[11px] text-gray-500 mb-0.5">{label}</p>
                <p className="text-sm font-semibold text-white">{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── tabs: positions / trade history ──────────────── */}
      <div className="card p-0 overflow-hidden">

        {/* tab header */}
        <div className="flex border-b border-[#2a2a2a]">
          {['positions', 'trades'].map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-5 py-3 text-xs font-medium capitalize transition-colors
                ${tab === t
                  ? 'border-b-2 border-blue-500 text-blue-400'
                  : 'text-gray-400 hover:text-gray-200'}`}
            >
              {t === 'positions' ? `Holdings (${positions.length})` : `Trade History (${trades.length})`}
            </button>
          ))}

          {/* refresh button */}
          <button
            onClick={loadAll}
            className="ml-auto px-4 text-gray-500 hover:text-gray-300 transition-colors"
            title="Refresh"
          >
            <RefreshCw size={13} />
          </button>
        </div>

        {/* positions table */}
        {tab === 'positions' && (
          <div className="overflow-x-auto">
            {positions.length === 0 ? (
              <div className="py-12 text-center">
                <p className="text-sm text-gray-500">No open positions</p>
                <p className="text-xs text-gray-600 mt-1">Place a buy order on the Market page to get started</p>
              </div>
            ) : (
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-[#2a2a2a] text-gray-500">
                    {['Symbol', 'Qty', 'Avg Buy', 'LTP', 'Invested', 'Current Value', 'Unrealized P&L', 'Return %'].map((h) => (
                      <th key={h} className="text-left px-4 py-2.5 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {positions.map((pos) => {
                    const invested     = pos.avg_buy_price * pos.quantity
                    const currentVal   = pos.current_price * pos.quantity
                    const returnPct    = ((currentVal - invested) / invested * 100).toFixed(2)
                    const pnlColor     = pos.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'
                    return (
                      <tr key={pos.id} className="border-b border-[#2a2a2a] hover:bg-[#252525] transition-colors">
                        <td className="px-4 py-3 font-semibold text-white">{pos.symbol}</td>
                        <td className="px-4 py-3 text-gray-200">{pos.quantity}</td>
                        <td className="px-4 py-3 text-gray-200">{inr(pos.avg_buy_price)}</td>
                        <td className="px-4 py-3 text-gray-200">{inr(pos.current_price)}</td>
                        <td className="px-4 py-3 text-gray-400">{inr(invested)}</td>
                        <td className="px-4 py-3 text-gray-200">{inr(currentVal)}</td>
                        <td className={`px-4 py-3 font-medium ${pnlColor}`}>
                          {pos.unrealized_pnl >= 0 ? '+' : ''}{inr(pos.unrealized_pnl)}
                        </td>
                        <td className={`px-4 py-3 font-medium ${pnlColor}`}>
                          {returnPct >= 0 ? '+' : ''}{returnPct}%
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* trade history table */}
        {tab === 'trades' && (
          <div className="overflow-x-auto">
            {trades.length === 0 ? (
              <div className="py-12 text-center">
                <p className="text-sm text-gray-500">No trades yet</p>
              </div>
            ) : (
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-[#2a2a2a] text-gray-500">
                    {['Symbol', 'Side', 'Qty', 'Fill Price', 'Slippage', 'Fees', 'P&L', 'Time'].map((h) => (
                      <th key={h} className="text-left px-4 py-2.5 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {trades.map((t) => {
                    const pnlColor = t.pnl >= 0 ? 'text-green-400' : 'text-red-400'
                    const date     = new Date(t.executed_at).toLocaleString('en-IN', {
                      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
                    })
                    return (
                      <tr key={t.id} className="border-b border-[#2a2a2a] hover:bg-[#252525] transition-colors">
                        <td className="px-4 py-3 font-semibold text-white">{t.symbol}</td>
                        <td className="px-4 py-3">
                          <span className={t.side === 'buy' ? 'badge-green' : 'badge-red'}>
                            {t.side.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-200">{t.quantity}</td>
                        <td className="px-4 py-3 text-gray-200">{inr(t.fill_price)}</td>
                        <td className="px-4 py-3 text-gray-400">{inr(t.slippage)}</td>
                        <td className="px-4 py-3 text-gray-400">{inr(t.transaction_cost)}</td>
                        <td className={`px-4 py-3 font-medium ${pnlColor}`}>
                          {t.pnl !== 0 ? (t.pnl >= 0 ? '+' : '') + inr(t.pnl) : '—'}
                        </td>
                        <td className="px-4 py-3 text-gray-500">{date}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}

      </div>
    </div>
  )
}

// small reusable stat card
function StatCard({ label, value, icon }) {
  return (
    <div className="card flex items-start justify-between">
      <div>
        <p className="text-xs text-gray-500 mb-1">{label}</p>
        <p className="text-base font-semibold text-white">{value}</p>
      </div>
      <div className="p-2 rounded-lg bg-[#252525]">{icon}</div>
    </div>
  )
}
