// OrderBookPanel.jsx
// Shows the live bid/ask depth for a stock
// Data comes from the WebSocket tick's order_book field
// bids = buyers waiting, asks = sellers waiting

export default function OrderBookPanel({ orderBook }) {
  if (!orderBook) return null

  const { bids, asks, spread, mid_price } = orderBook

  // find max quantity across all levels for the bar width scaling
  const allQtys = [...bids, ...asks].map((l) => l.quantity)
  const maxQty  = Math.max(...allQtys, 1)

  return (
    <div className="card p-3">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-white">Market Depth</h3>
        <div className="text-[10px] text-gray-500">
          Spread: <span className="text-gray-300">₹{spread}</span>
        </div>
      </div>

      {/* column headers */}
      <div className="grid grid-cols-3 text-[10px] text-gray-500 mb-1.5 px-1">
        <span>Price</span>
        <span className="text-center">Qty</span>
        <span className="text-right">Total</span>
      </div>

      {/* asks — shown in reverse so best ask is closest to mid */}
      <div className="space-y-0.5 mb-1">
        {[...asks].reverse().map((level, i) => {
          const barWidth = (level.quantity / maxQty) * 100
          const total    = (level.price * level.quantity).toLocaleString('en-IN', { maximumFractionDigits: 0 })
          return (
            <div key={i} className="relative grid grid-cols-3 text-[11px] px-1 py-0.5 rounded overflow-hidden">
              {/* red background bar showing depth */}
              <div
                className="absolute right-0 top-0 h-full bg-red-500/10"
                style={{ width: `${barWidth}%` }}
              />
              <span className="text-red-400 font-mono relative z-10">₹{level.price.toLocaleString('en-IN')}</span>
              <span className="text-gray-300 text-center relative z-10">{level.quantity.toLocaleString()}</span>
              <span className="text-gray-500 text-right relative z-10">{total}</span>
            </div>
          )
        })}
      </div>

      {/* mid price divider */}
      <div className="flex items-center gap-2 my-1.5 px-1">
        <div className="flex-1 h-px bg-[#2a2a2a]" />
        <span className="text-xs font-semibold text-white">₹{mid_price?.toLocaleString('en-IN')}</span>
        <div className="flex-1 h-px bg-[#2a2a2a]" />
      </div>

      {/* bids */}
      <div className="space-y-0.5 mt-1">
        {bids.map((level, i) => {
          const barWidth = (level.quantity / maxQty) * 100
          const total    = (level.price * level.quantity).toLocaleString('en-IN', { maximumFractionDigits: 0 })
          return (
            <div key={i} className="relative grid grid-cols-3 text-[11px] px-1 py-0.5 rounded overflow-hidden">
              {/* green background bar */}
              <div
                className="absolute left-0 top-0 h-full bg-green-500/10"
                style={{ width: `${barWidth}%` }}
              />
              <span className="text-green-400 font-mono relative z-10">₹{level.price.toLocaleString('en-IN')}</span>
              <span className="text-gray-300 text-center relative z-10">{level.quantity.toLocaleString()}</span>
              <span className="text-gray-500 text-right relative z-10">{total}</span>
            </div>
          )
        })}
      </div>

    </div>
  )
}
