import { useState, useEffect } from 'react'
import { RefreshCw, XCircle } from 'lucide-react'
import { getOrders, cancelOrder } from '../services/orders'

const inr = (n) =>
  n != null
    ? new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(n)
    : '—'

// status badge colors
const STATUS_STYLES = {
  filled:    'bg-green-500/10 text-green-400',
  pending:   'bg-yellow-500/10 text-yellow-400',
  cancelled: 'bg-gray-500/10 text-gray-400',
  rejected:  'bg-red-500/10 text-red-400',
}

export default function Orders() {
  const [orders,    setOrders]    = useState([])
  const [filter,    setFilter]    = useState('all')   // all | filled | pending | cancelled
  const [loading,   setLoading]   = useState(true)
  const [cancelling, setCancelling] = useState(null)  // order id being cancelled

  const loadOrders = () => {
    setLoading(true)
    getOrders()
      .then(setOrders)
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(loadOrders, [])

  const handleCancel = async (orderId) => {
    setCancelling(orderId)
    try {
      await cancelOrder(orderId)
      // update locally instead of full reload — feels faster
      setOrders((prev) =>
        prev.map((o) => o.id === orderId ? { ...o, status: 'cancelled' } : o)
      )
    } catch (err) {
      alert(err.response?.data?.detail || 'Could not cancel order.')
    } finally {
      setCancelling(null)
    }
  }

  const filtered = filter === 'all' ? orders : orders.filter((o) => o.status === filter)

  // count per status for the filter tabs
  const counts = {
    all:       orders.length,
    filled:    orders.filter((o) => o.status === 'filled').length,
    pending:   orders.filter((o) => o.status === 'pending').length,
    cancelled: orders.filter((o) => o.status === 'cancelled').length,
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-4 max-w-6xl">

      {/* header */}
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-white">Order History</h2>
        <button
          onClick={loadOrders}
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 transition-colors"
        >
          <RefreshCw size={12} />
          Refresh
        </button>
      </div>

      {/* filter tabs */}
      <div className="flex gap-1 bg-[#1a1a1a] rounded-xl p-1 w-fit border border-[#2a2a2a]">
        {['all', 'filled', 'pending', 'cancelled'].map((tab) => (
          <button
            key={tab}
            onClick={() => setFilter(tab)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors
              ${filter === tab
                ? 'bg-[#2a2a2a] text-white'
                : 'text-gray-500 hover:text-gray-300'}`}
          >
            {tab}
            <span className="ml-1.5 text-[10px] text-gray-500">({counts[tab]})</span>
          </button>
        ))}
      </div>

      {/* orders table */}
      <div className="card p-0 overflow-hidden">
        {filtered.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-sm text-gray-500">No {filter === 'all' ? '' : filter} orders yet</p>
            <p className="text-xs text-gray-600 mt-1">
              {filter === 'all' ? 'Go to the Market page to place your first order.' : `Try switching to a different filter.`}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-[#2a2a2a] text-gray-500">
                  {['#', 'Symbol', 'Side', 'Type', 'Qty', 'Limit Price', 'Fill Price', 'Slippage', 'Status', 'Placed At', ''].map((h) => (
                    <th key={h} className="text-left px-4 py-3 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((order) => {
                  const date = new Date(order.created_at).toLocaleString('en-IN', {
                    day: '2-digit', month: 'short', year: '2-digit',
                    hour: '2-digit', minute: '2-digit',
                  })

                  return (
                    <tr
                      key={order.id}
                      className="border-b border-[#2a2a2a] hover:bg-[#252525] transition-colors"
                    >
                      <td className="px-4 py-3 text-gray-600">#{order.id}</td>

                      <td className="px-4 py-3 font-semibold text-white">{order.symbol}</td>

                      <td className="px-4 py-3">
                        <span className={order.side === 'buy' ? 'badge-green' : 'badge-red'}>
                          {order.side.toUpperCase()}
                        </span>
                      </td>

                      <td className="px-4 py-3 text-gray-400 capitalize">{order.order_type}</td>

                      <td className="px-4 py-3 text-gray-200">{order.quantity}</td>

                      {/* limit price — only set for limit orders */}
                      <td className="px-4 py-3 text-gray-400">
                        {order.price ? inr(order.price) : <span className="text-gray-600">—</span>}
                      </td>

                      {/* actual fill price */}
                      <td className="px-4 py-3 text-gray-200">
                        {order.filled_price ? inr(order.filled_price) : <span className="text-gray-600">—</span>}
                      </td>

                      {/* slippage cost */}
                      <td className="px-4 py-3 text-gray-400">
                        {order.slippage != null && order.slippage > 0
                          ? <span className="text-orange-400">{inr(order.slippage)}</span>
                          : <span className="text-gray-600">—</span>
                        }
                      </td>

                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium
                          ${STATUS_STYLES[order.status] ?? 'text-gray-400'}`}>
                          {order.status}
                        </span>
                      </td>

                      <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{date}</td>

                      {/* cancel button — only for pending orders */}
                      <td className="px-4 py-3">
                        {order.status === 'pending' && (
                          <button
                            onClick={() => handleCancel(order.id)}
                            disabled={cancelling === order.id}
                            className="flex items-center gap-1 text-[11px] text-gray-500
                                       hover:text-red-400 transition-colors disabled:opacity-40"
                            title="Cancel order"
                          >
                            <XCircle size={13} />
                            {cancelling === order.id ? '...' : 'Cancel'}
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* summary row at the bottom */}
      {orders.length > 0 && (
        <div className="flex gap-6 text-xs text-gray-500 px-1">
          <span>Total: <span className="text-gray-300">{orders.length}</span></span>
          <span>Filled: <span className="text-green-400">{counts.filled}</span></span>
          <span>Pending: <span className="text-yellow-400">{counts.pending}</span></span>
          <span>Cancelled: <span className="text-gray-400">{counts.cancelled}</span></span>
        </div>
      )}

    </div>
  )
}
