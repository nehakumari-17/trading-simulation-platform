// shows the live price ticker at the top of the market page
// quote = { symbol, ltp, open, high, low, close, change, change_pct, volume }
export default function QuoteBar({ quote }) {
  if (!quote) return null

  const isUp      = quote.change >= 0
  const color     = isUp ? 'text-green-400' : 'text-red-400'
  const bgColor   = isUp ? 'bg-green-500/10' : 'bg-red-500/10'
  const sign      = isUp ? '+' : ''

  const fmt = (n) => n?.toLocaleString('en-IN', { maximumFractionDigits: 2 })

  return (
    <div className="flex flex-wrap items-center gap-4 px-4 py-3
                    bg-[#1e1e1e] rounded-xl border border-[#2a2a2a]">

      {/* symbol + LTP */}
      <div className="flex items-baseline gap-3">
        <span className="text-base font-bold text-white">{quote.symbol}</span>
        <span className="text-2xl font-semibold text-white">₹{fmt(quote.ltp)}</span>
        <span className={`text-sm font-medium px-2 py-0.5 rounded-full ${bgColor} ${color}`}>
          {sign}{fmt(quote.change)} ({sign}{quote.change_pct}%)
        </span>
      </div>

      {/* OHLV stats */}
      <div className="flex gap-5 ml-auto text-xs">
        {[
          { label: 'Open',  value: fmt(quote.open)  },
          { label: 'High',  value: fmt(quote.high)  },
          { label: 'Low',   value: fmt(quote.low)   },
          { label: 'Prev',  value: fmt(quote.close) },
          { label: 'Vol',   value: (quote.volume / 1_000).toFixed(0) + 'K' },
        ].map(({ label, value }) => (
          <div key={label} className="text-center">
            <p className="text-gray-500">{label}</p>
            <p className="text-gray-200 font-medium">{value}</p>
          </div>
        ))}
      </div>

    </div>
  )
}
