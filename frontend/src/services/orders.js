import api from './api'

// place a new order
// orderData = { symbol, order_type, side, quantity, price? }
export const placeOrder = async (orderData) => {
  const res = await api.post('/orders/', orderData)
  return res.data
}

// get all orders for the logged-in user
export const getOrders = async () => {
  const res = await api.get('/orders/')
  return res.data
}

// cancel a pending limit order by id
export const cancelOrder = async (orderId) => {
  const res = await api.delete(`/orders/${orderId}`)
  return res.data
}
