import { useState } from 'react'
import { placeOrder } from '../services/orders'

// buy/sell order form shown on the right side of the market page
// onOrderPlaced is called after a successful order so the parent can refresh
export default function OrderForm({ symbol, currentPrice, onOrderPlaced }) {
  const [side, setSide]           = useState('buy')   // 'buy' | 'sell'
  const [orderType, setOrderType] = useState('market') // 'market' | 'limit'
  const [quantity, setQuantity]   = useState('')
  const [price, setPrice]         = useState('')
  const [loading, setLoading]     = useState(false)
  const [msg, setMsg]             = useState(null)     // { type: 'success'|'error', text }

  // rough total cost estimate shown below the form
  const fillPrice   = orderType === 'limit' && price ? parseFloat(price) : currentPrice
  const totalEst    = fillPrice && quantity ? (fillPrice * parseInt(quantity)).toLocaleString('en-IN') : '—'

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setMsg(null)

    const payload = {
      symbol,
      order_type: orderType,
      side,
      quantity:   parseInt(quantity),
      price:      orderType === 'limit' ? parseFloat(price) : undefined,
    }

    try {
      await placeOrder(payload)
      setMsg({ type: 'success', text: `${side.toUpperCase()} order placed successfully!` })
      setQuantity('')
      setPrice('')
      onOrderPlaced?.()
    } catch (err) {
      const text = err.response?.data?.detail || 'Order failed. Try again.'
      setMsg({ type: 'error', text })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card space-y-4">
      <h3 className="text-sm font-semibold text-white">Place Order</h3>

      {/* buy / sell toggle */}
      <div className="flex rounded-lg overflow-hidden border border-[#333] text-xs font-medium">
        <button
          onClick={() => setSide('buy')}
          className={`flex-1 py-2 transition-colors
            ${side === 'buy' ? 'bg-green-600 text-white' : 'text-gray-400 hover:text-white'}`}
        >
          BUY
        </button>
        <button
          onClick={() => setSide('sell')}
          className={`flex-1 py-2 transition-colors
            ${side === 'sell' ? 'bg-red-600 text-white' : 'text-gray-400 hover:text-white'}`}
        >
          SELL
        </button>
      </div>

      {/* order type */}
      <div className="flex gap-2 text-xs">
        {['market', 'limit'].map((t) => (
          <button
            key={t}
            onClick={() => setOrderType(t)}
            className={`px-3 py-1.5 rounded-lg border transition-colors capitalize
              ${orderType === t
                ? 'border-blue-500 text-blue-400 bg-blue-500/10'
                : 'border-[#333] text-gray-400 hover:border-gray-500'}`}
          >
            {t}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">

        {/* stock symbol — locked to whatever's selected */}
        <div>
          <label className="block text-xs text-gray-400 mb-1">Symbol</label>
          <input value={symbol || '—'} readOnly className="input opacity-60 cursor-not-allowed" />
        </div>

        {/* limit price — only shown for limit orders */}
        {orderType === 'limit' && (
          <div>
            <label className="block text-xs text-gray-400 mb-1">Limit Price (₹)</label>
            <input
              type="number"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="e.g. 2450.00"
              className="input"
              min="0.01"
              step="0.05"
              required
            />
          </div>
        )}

        <div>
          <label className="block text-xs text-gray-400 mb-1">Quantity (shares)</label>
          <input
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="e.g. 10"
            className="input"
            min="1"
            step="1"
            required
          />
        </div>

        {/* estimated cost */}
        <div className="flex justify-between text-xs text-gray-500 px-1">
          <span>Est. Value</span>
          <span className="text-gray-300">₹{totalEst}</span>
        </div>

        <button
          type="submit"
          disabled={loading || !symbol}
          className={`w-full py-2.5 rounded-lg font-semibold text-sm transition-colors
            disabled:opacity-50 disabled:cursor-not-allowed
            ${side === 'buy' ? 'btn-buy' : 'btn-sell'}`}
        >
          {loading ? 'Placing...' : `${side === 'buy' ? 'Buy' : 'Sell'} ${symbol || ''}`}
        </button>
      </form>

      {/* success / error feedback */}
      {msg && (
        <div className={`text-xs px-3 py-2 rounded-lg
          ${msg.type === 'success'
            ? 'bg-green-500/10 text-green-400 border border-green-500/20'
            : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
          {msg.text}
        </div>
      )}
    </div>
  )
}
