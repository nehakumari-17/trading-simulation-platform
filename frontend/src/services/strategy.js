import api from './api'

// run a backtest strategy for a symbol over a date range
// strategyName = 'ma_crossover' | 'rsi' | 'vwap'
export const runStrategy = async (symbol, strategyName, startDate, endDate) => {
  const res = await api.post(
    `/strategy/run?symbol=${symbol}&strategy_name=${strategyName}&start_date=${startDate}&end_date=${endDate}`
  )
  return res.data
}

// get all past strategy runs for this user
export const getStrategyHistory = async () => {
  const res = await api.get('/strategy/history')
  return res.data
}
