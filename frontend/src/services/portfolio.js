import api from './api'

// full portfolio — cash, positions, P&L
export const getPortfolio = async () => {
  const res = await api.get('/portfolio')
  return res.data
}

// just the quick summary numbers for the dashboard cards
export const getSummary = async () => {
  const res = await api.get('/portfolio/summary')
  return res.data
}

// list of all open positions (stocks currently held)
export const getPositions = async () => {
  const res = await api.get('/portfolio/positions')
  return res.data
}

// trade history — every filled buy and sell
export const getTrades = async () => {
  const res = await api.get('/portfolio/trades')
  return res.data
}

// performance metrics — sharpe, win rate, drawdown etc
export const getPerformance = async () => {
  const res = await api.get('/portfolio/performance')
  return res.data
}
