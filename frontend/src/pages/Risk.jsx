import { useState, useEffect } from 'react'
import { Shield, AlertTriangle, TrendingDown, PieChart, RefreshCw } from 'lucide-react'
import { getPositions, getPerformance, getSummary } from '../services/portfolio'

const inr = (n) =>
  n != null
    ? new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n)
    : '—'

// simple progress bar — used for exposure and concentration visuals
function ProgressBar({ value, max = 100, color = 'bg-blue-500' }) {
  const pct = Math.min((value / max) * 100, 100)
  return (
    <div className="w-full bg-[#2a2a2a] rounded-full h-1.5 mt-1.5">
      <div className={`h-1.5 rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
    </div>
  )
}

export default function Risk() {
  const [summary,     setSummary]     = useState(null)
  const [positions,   setPositions]   = useState([])
  const [performance, setPerformance] = useState(null)
  const [loading,     setLoading]     = useState(true)

  const loadAll = () => {
    setLoading(true)
    Promise.all([getSummary(), getPositions(), getPerformance()])
      .then(([s, p, perf]) => {
        setSummary(s)
        setPositions(p)
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

  const totalValue    = summary?.total_value    ?? 0
  const cashBalance   = summary?.cash_balance   ?? 0
  const holdingsValue = summary?.holdings_value ?? 0

  // cash as a % of total portfolio
  const cashPct       = totalValue > 0 ? (cashBalance / totalValue) * 100 : 100
  // how much is deployed in the market
  const exposurePct   = totalValue > 0 ? (holdingsValue / totalValue) * 100 : 0

  // warnings — things that might need attention
  const warnings = []
  if (cashPct < 5)  warnings.push('Cash reserve is below 5% — low liquidity if you need to act quickly.')
  if (exposurePct > 90) warnings.push('Over 90% of your portfolio is deployed — very high market exposure.')
  if (performance?.max_drawdown > 50000) warnings.push(`Max drawdown has crossed ₹${(performance.max_drawdown / 1000).toFixed(0)}K — review your strategy.`)

  // sort positions by value so we can show concentration easily
  const sortedPositions = [...positions].sort(
    (a, b) => b.current_price * b.quantity - a.current_price * a.quantity
  )

  return (
    <div className="space-y-4 max-w-5xl">

      {/* ── page header ─────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield size={18} className="text-blue-400" />
          <h2 className="text-base font-semibold text-white">Risk Overview</h2>
        </div>
        <button
          onClick={loadAll}
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 transition-colors"
        >
          <RefreshCw size={12} />
          Refresh
        </button>
      </div>

      {/* ── warnings banner ──────────────────────────────── */}
      {warnings.length > 0 && (
        <div className="space-y-2">
          {warnings.map((w, i) => (
            <div key={i} className="flex items-start gap-2 px-3 py-2.5 rounded-lg
                                    bg-yellow-500/8 border border-yellow-500/20">
              <AlertTriangle size={13} className="text-yellow-400 mt-0.5 shrink-0" />
              <p className="text-xs text-yellow-300">{w}</p>
            </div>
          ))}
        </div>
      )}

      {warnings.length === 0 && (
        <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg
                        bg-green-500/8 border border-green-500/20">
          <Shield size={13} className="text-green-400" />
          <p className="text-xs text-green-300">No risk warnings — portfolio looks healthy.</p>
        </div>
      )}

      {/* ── exposure overview ────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">

        <div className="card">
          <p className="text-xs text-gray-500">Market Exposure</p>
          <p className="text-xl font-semibold text-white mt-1">{exposurePct.toFixed(1)}%</p>
          <ProgressBar
            value={exposurePct}
            color={exposurePct > 80 ? 'bg-red-500' : exposurePct > 60 ? 'bg-yellow-500' : 'bg-blue-500'}
          />
          <p className="text-[11px] text-gray-500 mt-2">{inr(holdingsValue)} in stocks</p>
        </div>

        <div className="card">
          <p className="text-xs text-gray-500">Cash Reserve</p>
          <p className="text-xl font-semibold text-white mt-1">{cashPct.toFixed(1)}%</p>
          <ProgressBar
            value={cashPct}
            color={cashPct < 5 ? 'bg-red-500' : cashPct < 15 ? 'bg-yellow-500' : 'bg-green-500'}
          />
          <p className="text-[11px] text-gray-500 mt-2">{inr(cashBalance)} available</p>
        </div>

        <div className="card">
          <p className="text-xs text-gray-500">Open Positions</p>
          <p className="text-xl font-semibold text-white mt-1">{positions.length}</p>
          <ProgressBar value={positions.length} max={10} color="bg-purple-500" />
          <p className="text-[11px] text-gray-500 mt-2">
            {positions.length === 0 ? 'No open positions' : `Across ${positions.length} stock${positions.length > 1 ? 's' : ''}`}
          </p>
        </div>

      </div>

      {/* ── position concentration ───────────────────────── */}
      {sortedPositions.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <PieChart size={14} className="text-gray-400" />
            <h3 className="text-sm font-semibold text-white">Position Concentration</h3>
            <span className="text-xs text-gray-500 ml-1">— recommended max per stock is 30%</span>
          </div>

          <div className="space-y-3">
            {sortedPositions.map((pos) => {
              const posValue  = pos.current_price * pos.quantity
              const posWeight = totalValue > 0 ? (posValue / totalValue) * 100 : 0
              const isHigh    = posWeight > 30
              const pnlColor  = pos.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'

              return (
                <div key={pos.id}>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white">{pos.symbol}</span>
                      <span className="text-gray-500">{pos.quantity} shares @ {inr(pos.avg_buy_price)}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={pnlColor}>
                        {pos.unrealized_pnl >= 0 ? '+' : ''}{inr(pos.unrealized_pnl)}
                      </span>
                      <span className={`font-semibold ${isHigh ? 'text-yellow-400' : 'text-gray-200'}`}>
                        {posWeight.toFixed(1)}%
                        {isHigh && <AlertTriangle size={10} className="inline ml-1 text-yellow-400" />}
                      </span>
                    </div>
                  </div>
                  <ProgressBar
                    value={posWeight}
                    color={isHigh ? 'bg-yellow-500' : 'bg-blue-500'}
                  />
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── drawdown and volatility from performance ─────── */}
      {performance && performance.total_trades > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <TrendingDown size={14} className="text-red-400" />
            <h3 className="text-sm font-semibold text-white">Historical Risk Metrics</h3>
            <span className="text-xs text-gray-500 ml-1">— based on your closed trades</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div>
              <p className="text-gray-500 mb-1">Max Drawdown</p>
              <p className="text-red-400 font-semibold text-sm">{inr(performance.max_drawdown)}</p>
              <p className="text-gray-600 mt-0.5">Worst peak-to-trough loss</p>
            </div>
            <div>
              <p className="text-gray-500 mb-1">Sharpe Ratio</p>
              <p className={`font-semibold text-sm ${performance.sharpe_ratio > 1 ? 'text-green-400' : performance.sharpe_ratio > 0 ? 'text-yellow-400' : 'text-red-400'}`}>
                {performance.sharpe_ratio?.toFixed(2)}
              </p>
              <p className="text-gray-600 mt-0.5">Return per unit of risk</p>
            </div>
            <div>
              <p className="text-gray-500 mb-1">Win Rate</p>
              <p className={`font-semibold text-sm ${performance.win_rate > 50 ? 'text-green-400' : 'text-red-400'}`}>
                {performance.win_rate}%
              </p>
              <p className="text-gray-600 mt-0.5">Trades closed in profit</p>
            </div>
            <div>
              <p className="text-gray-500 mb-1">Profit Factor</p>
              <p className={`font-semibold text-sm ${performance.profit_factor > 1 ? 'text-green-400' : 'text-red-400'}`}>
                {performance.profit_factor?.toFixed(2)}
              </p>
              <p className="text-gray-600 mt-0.5">Gross profit / gross loss</p>
            </div>
          </div>
        </div>
      )}

      {/* empty state — no positions yet */}
      {positions.length === 0 && (
        <div className="card flex items-center justify-center py-12">
          <div className="text-center">
            <Shield size={32} className="text-gray-600 mx-auto mb-2" />
            <p className="text-sm text-gray-400">No positions to analyse</p>
            <p className="text-xs text-gray-600 mt-1">Place some trades on the Market page first</p>
          </div>
        </div>
      )}

    </div>
  )
}
