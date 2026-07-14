import { useState, useEffect } from 'react'
import { PlayCircle, Clock, TrendingUp, TrendingDown } from 'lucide-react'
import { runStrategy, getStrategyHistory } from '../services/strategy'
import { getInstruments } from '../services/market'

// quick helper for INR formatting
const inr = (n) =>
  n != null
    ? new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(n)
    : '—'

const STRATEGIES = [
  { value: 'ma_crossover', label: 'Moving Average Crossover', desc: 'Buy on golden cross, sell on death cross (20/50 day MA)' },
  { value: 'rsi',          label: 'RSI Strategy',             desc: 'Buy when RSI < 30 (oversold), sell when RSI > 70 (overbought)' },
  { value: 'vwap',         label: 'VWAP Strategy',            desc: 'Buy when price crosses above VWAP, sell when it drops below' },
]

export default function Strategy() {
  const [instruments, setInstruments] = useState([])
  const [history,     setHistory]     = useState([])
  const [result,      setResult]      = useState(null)
  const [running,     setRunning]     = useState(false)
  const [error,       setError]       = useState('')

  const [form, setForm] = useState({
    symbol:       '',
    strategyName: 'ma_crossover',
    startDate:    '2023-01-01',
    endDate:      '2024-01-01',
  })

  useEffect(() => {
    getInstruments().then(setInstruments).catch(console.error)
    loadHistory()
  }, [])

  const loadHistory = () => {
    getStrategyHistory().then(setHistory).catch(console.error)
  }

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
    setError('')
  }

  const handleRun = async (e) => {
    e.preventDefault()
    if (!form.symbol) { setError('Please select a symbol.'); return }

    setRunning(true)
    setResult(null)
    setError('')

    try {
      const data = await runStrategy(form.symbol, form.strategyName, form.startDate, form.endDate)
      setResult(data)
      loadHistory()
    } catch (err) {
      setError(err.response?.data?.detail || 'Strategy run failed. Try again.')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="space-y-4 max-w-6xl">

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* ── left: run form ───────────────────────────── */}
        <div className="space-y-4">

          {/* strategy cards */}
          <div className="space-y-2">
            {STRATEGIES.map((s) => (
              <button
                key={s.value}
                onClick={() => setForm({ ...form, strategyName: s.value })}
                className={`w-full text-left p-3 rounded-xl border transition-colors
                  ${form.strategyName === s.value
                    ? 'border-blue-500 bg-blue-500/10'
                    : 'border-[#2a2a2a] bg-[#1e1e1e] hover:border-[#3a3a3a]'}`}
              >
                <p className={`text-sm font-medium ${form.strategyName === s.value ? 'text-blue-400' : 'text-white'}`}>
                  {s.label}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">{s.desc}</p>
              </button>
            ))}
          </div>

          {/* run form */}
          <form onSubmit={handleRun} className="card space-y-3">
            <h3 className="text-sm font-semibold text-white">Backtest Settings</h3>

            {error && (
              <div className="text-xs px-3 py-2 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20">
                {error}
              </div>
            )}

            <div>
              <label className="block text-xs text-gray-400 mb-1">Symbol</label>
              <select
                name="symbol"
                value={form.symbol}
                onChange={handleChange}
                className="input"
                required
              >
                <option value="">Select a stock</option>
                {instruments.map((i) => (
                  <option key={i.symbol} value={i.symbol}>
                    {i.symbol} — {i.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-gray-400 mb-1">Start Date</label>
              <input
                type="date"
                name="startDate"
                value={form.startDate}
                onChange={handleChange}
                className="input"
                required
              />
            </div>

            <div>
              <label className="block text-xs text-gray-400 mb-1">End Date</label>
              <input
                type="date"
                name="endDate"
                value={form.endDate}
                onChange={handleChange}
                className="input"
                required
              />
            </div>

            <button
              type="submit"
              disabled={running}
              className="w-full btn-primary py-2.5 flex items-center justify-center gap-2
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <PlayCircle size={15} />
              {running ? 'Running...' : 'Run Backtest'}
            </button>
          </form>
        </div>

        {/* ── right: results ───────────────────────────── */}
        <div className="lg:col-span-2 space-y-4">

          {!result && !running && (
            <div className="card flex items-center justify-center h-48">
              <div className="text-center">
                <PlayCircle size={32} className="text-gray-600 mx-auto mb-2" />
                <p className="text-sm text-gray-500">Select a strategy and run a backtest</p>
                <p className="text-xs text-gray-600 mt-1">Results will appear here</p>
              </div>
            </div>
          )}

          {running && (
            <div className="card flex items-center justify-center h-48">
              <div className="flex items-center gap-3 text-gray-400">
                <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-sm">Running backtest...</span>
              </div>
            </div>
          )}

          {result && !running && (
            <>
              {/* summary metrics */}
              {result.total_trades === 0 ? (
                <div className="card text-center py-8">
                  <p className="text-sm text-gray-400">{result.message || 'No trades were generated in this period.'}</p>
                  <p className="text-xs text-gray-600 mt-1">Try a longer date range or a different symbol.</p>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
                    {[
                      { label: 'Total Trades',  value: result.total_trades,                     color: 'text-white'      },
                      { label: 'Win Rate',      value: `${result.win_rate}%`,                   color: 'text-white'      },
                      { label: 'Total Return',  value: inr(result.total_return),                color: result.total_return >= 0 ? 'text-green-400' : 'text-red-400' },
                      { label: 'Profit Factor', value: result.profit_factor?.toFixed(2),        color: 'text-white'      },
                      { label: 'Sharpe Ratio',  value: result.sharpe_ratio?.toFixed(2),         color: 'text-white'      },
                      { label: 'Max Drawdown',  value: inr(result.max_drawdown),               color: 'text-red-400'    },
                    ].map(({ label, value, color }) => (
                      <div key={label} className="card py-3">
                        <p className="text-[11px] text-gray-500 mb-1">{label}</p>
                        <p className={`text-sm font-semibold ${color}`}>{value}</p>
                      </div>
                    ))}
                  </div>

                  {/* trade list */}
                  <div className="card p-0 overflow-hidden">
                    <div className="px-4 py-3 border-b border-[#2a2a2a]">
                      <h3 className="text-xs font-semibold text-gray-300">
                        Trade-by-Trade Breakdown — {result.symbol} ({result.strategy})
                      </h3>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="border-b border-[#2a2a2a] text-gray-500">
                            {['Entry Date', 'Exit Date', 'Entry Price', 'Exit Price', 'P&L', 'Signal'].map((h) => (
                              <th key={h} className="text-left px-4 py-2.5 font-medium">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {result.trades.map((t, i) => (
                            <tr key={i} className="border-b border-[#2a2a2a] hover:bg-[#252525] transition-colors">
                              <td className="px-4 py-2.5 text-gray-400">{t.entry_date}</td>
                              <td className="px-4 py-2.5 text-gray-400">{t.exit_date}</td>
                              <td className="px-4 py-2.5 text-gray-200">₹{t.entry_price?.toLocaleString('en-IN')}</td>
                              <td className="px-4 py-2.5 text-gray-200">₹{t.exit_price?.toLocaleString('en-IN')}</td>
                              <td className={`px-4 py-2.5 font-medium ${t.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {t.pnl >= 0 ? '+' : ''}₹{t.pnl?.toLocaleString('en-IN')}
                              </td>
                              <td className="px-4 py-2.5 text-gray-500">{t.signal}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              )}
            </>
          )}

          {/* past runs */}
          {history.length > 0 && (
            <div className="card p-0 overflow-hidden">
              <div className="px-4 py-3 border-b border-[#2a2a2a] flex items-center gap-2">
                <Clock size={13} className="text-gray-500" />
                <h3 className="text-xs font-semibold text-gray-300">Past Strategy Runs</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-[#2a2a2a] text-gray-500">
                      {['Strategy', 'Symbol', 'Period', 'Trades', 'Return', 'Win Rate', 'Sharpe'].map((h) => (
                        <th key={h} className="text-left px-4 py-2 font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((r) => (
                      <tr key={r.id} className="border-b border-[#2a2a2a] hover:bg-[#252525]">
                        <td className="px-4 py-2.5 text-gray-200 capitalize">{r.strategy_name?.replace('_', ' ')}</td>
                        <td className="px-4 py-2.5 font-semibold text-white">{r.symbol}</td>
                        <td className="px-4 py-2.5 text-gray-500">{r.start_date} → {r.end_date}</td>
                        <td className="px-4 py-2.5 text-gray-200">{r.total_trades ?? '—'}</td>
                        <td className={`px-4 py-2.5 font-medium ${(r.total_return ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {r.total_return != null ? inr(r.total_return) : '—'}
                        </td>
                        <td className="px-4 py-2.5 text-gray-200">{r.win_rate != null ? `${r.win_rate}%` : '—'}</td>
                        <td className="px-4 py-2.5 text-gray-200">{r.sharpe_ratio?.toFixed(2) ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  )
}
