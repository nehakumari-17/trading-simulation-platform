import api from './api'

// get all available stocks (for watchlist / search dropdown)
export const getInstruments = async () => {
  const res = await api.get('/market/instruments')
  return res.data
}

// search by partial name or symbol — e.g. "tata", "HDFC"
export const searchInstruments = async (query) => {
  const res = await api.get(`/market/search?q=${query}`)
  return res.data
}

// get current quote for a stock — LTP, change, volume etc
export const getQuote = async (symbol) => {
  const res = await api.get(`/market/quote/${symbol}`)
  return res.data
}

// get OHLCV candles for the chart
// limit = how many candles to show (default 100)
export const getCandles = async (symbol, limit = 100) => {
  const res = await api.get(`/market/candles/${symbol}?limit=${limit}`)
  return res.data
}
