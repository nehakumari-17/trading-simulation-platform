import { useState, useEffect, useRef } from 'react'
import { Search, ChevronUp, ChevronDown } from 'lucide-react'
import { getInstruments, getQuote, getCandles } from '../services/market'
import { getOrders } from '../services/orders'
import CandleChart from '../components/CandleChart'
import QuoteBar    from '../components/QuoteBar'
import OrderForm   from '../components/OrderForm'

export default function Market() {
  const [instruments, setInstruments]   = useState([])
  const [searchQuery, setSearchQuery]   = useState('')
  const [selectedSymbol, setSymbol]     = useState(null)
  const [quote, setQuote]               = useState(null)
  const [candles, setCandles]           = useState([])
  const [orders, setOrders]             = useState([])
  const [loadingChart, setLoadingChart] = useState(false)

  // websocket ref for live price ticks
  const wsRef = useRef(null)

  // load instrument list on mount
  useEffect(() => {
    getInstruments()
      .then(setInstruments)
      .catch(console.error)
  }, [])

  // whenever the user picks a stock, fetch its quote + candles
  useEffect(() => {
    if (!selectedSymbol) return

    setLoadingChart(true)
    setQuote(null)
    setCandles([])

    Promise.all([
      getQuote(selectedSymbol),
      getCandles(selectedSymbol, 200),
    ])
      .then(([q, c]) => {
        setQuote(q)
        setCandles(c)
      })
      .catch(console.error)
      .finally(() => setLoadingChart(false))

    // open websocket for live price ticks
    // close the old one first if switching stocks
    if (wsRef.current) wsRef.current.close()

    const ws = new WebSocket(`ws://localhost:8000/ws/prices/${selectedSymbol}`)
    ws.onmessage = (e) => {
      const tick = JSON.parse(e.data)
      if (tick.error) return
      // update just the LTP and change in the quote — no full reload needed
      setQuote((prev) => prev ? {
        ...prev,
        ltp:        tick.ltp,
        change:     tick.change,
        change_pct: tick.change_pct,
      } : prev)
    }
    wsRef.current = ws

    return () => ws.close()
  }, [selectedSymbol])

  // close ws on unmount
  useEffect(() => {
    return () => wsRef.current?.close()
  }, [])

  const loadOrders = () => {
    getOrders().then(setOrders).catch(console.error)
  }

  useEffect(loadOrders, [selectedSymbol])

  // filtered watchlist based on search input
  const filtered = instruments.filter((i) =>
    i.symbol.includes(searchQuery.toUpperCase()) ||
    i.name.toUpperCase().includes(searchQuery.toUpperCase())
  )

  return (
    <div className="flex gap-4 h-full">

      {/* ── left: watchlist ─────────────────────────────── */}
      <div className="w-60 shrink-0 flex flex-col gap-3">

        {/* search box */}
        <div className="relative">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search symbol..."
            className="input pl-8 text-xs"
          />
        </div>

        {/* stock list */}
        <div className="card flex-1 overflow-y-auto p-0">
          {filtered.length === 0 && (
            <p className="text-xs text-gray-500 text-center py-6">No results</p>
          )}
          {filtered.map((inst) => {
            const isSelected = inst.symbol === selectedSymbol
            const isUp = inst.last_price > 0 // TODO: compare with prev close when available
            return (
              <button
                key={inst.symbol}
                onClick={() => setSymbol(inst.symbol)}
                className={`w-full flex items-center justify-between px-3 py-2.5
                            text-left text-xs transition-colors border-b border-[#2a2a2a] last:border-0
                            ${isSelected ? 'bg-blue-600/15 text-blue-300' : 'hover:bg-[#252525] text-gray-300'}`}
              >
                <div>
                  <p className="font-medium">{inst.symbol}</p>
                  <p className="text-gray-500 text-[10px] mt-0.5 truncate w-28">{inst.name}</p>
                </div>
                <p className="font-mono text-gray-200">
                  ₹{inst.last_price?.toLocaleString('en-IN')}
                </p>
              </button>
            )
          })}
        </div>
      </div>

      {/* ── center: chart area ──────────────────────────── */}
      <div className="flex-1 flex flex-col gap-3 min-w-0">

        {!selectedSymbol ? (
          // placeholder when nothing is selected yet
          <div className="flex-1 card flex items-center justify-center">
            <div className="text-center">
              <p className="text-gray-400 text-sm">Select a stock to view chart</p>
              <p className="text-gray-600 text-xs mt-1">Choose from the watchlist on the left</p>
            </div>
          </div>
        ) : (
          <>
            {/* price ticker */}
            <QuoteBar quote={quote} />

            {/* candlestick chart */}
            <div className="card flex-1">
              {loadingChart ? (
                <div className="flex items-center justify-center h-80">
                  <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : (
                <CandleChart candles={candles} symbol={selectedSymbol} />
              )}
            </div>

            {/* recent orders for this stock */}
            <div className="card">
              <h3 className="text-xs font-semibold text-gray-400 mb-3">Recent Orders — {selectedSymbol}</h3>
              {orders.length === 0 ? (
                <p className="text-xs text-gray-600">No orders yet</p>
              ) : (
                <div className="space-y-1">
                  {orders.slice(0, 5).map((o) => (
                    <div key={o.id}
                      className="flex justify-between items-center text-xs py-1.5
                                 border-b border-[#2a2a2a] last:border-0">
                      <div className="flex items-center gap-2">
                        <span className={o.side === 'buy' ? 'text-green-400' : 'text-red-400'}>
                          {o.side.toUpperCase()}
                        </span>
                        <span className="text-gray-400">{o.quantity} shares</span>
                        <span className="text-gray-500">{o.order_type}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-gray-200">₹{o.filled_price?.toLocaleString('en-IN') ?? '—'}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[10px]
                          ${o.status === 'filled'    ? 'badge-green' :
                            o.status === 'cancelled' ? 'bg-gray-500/10 text-gray-400' :
                                                       'bg-yellow-500/10 text-yellow-400'}`}>
                          {o.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* ── right: order form ───────────────────────────── */}
      <div className="w-64 shrink-0">
        <OrderForm
          symbol={selectedSymbol}
          currentPrice={quote?.ltp}
          onOrderPlaced={loadOrders}
        />
      </div>

    </div>
  )
}
