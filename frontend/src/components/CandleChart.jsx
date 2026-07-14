import { useEffect, useRef } from 'react'
import { createChart } from 'lightweight-charts'

// renders a candlestick chart using TradingView's lightweight-charts library
// candles = array of { timestamp, open, high, low, close, volume }
export default function CandleChart({ candles, symbol }) {
  const containerRef = useRef(null)
  const chartRef     = useRef(null)
  const seriesRef    = useRef(null)

  // create the chart once on mount
  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: '#1e1e1e' },
        textColor:  '#9ca3af',
      },
      grid: {
        vertLines:  { color: '#2a2a2a' },
        horzLines:  { color: '#2a2a2a' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#2a2a2a',
      },
      timeScale: {
        borderColor:     '#2a2a2a',
        timeVisible:      true,
        secondsVisible:   false,
      },
      width:  containerRef.current.clientWidth,
      height: 380,
    })

    const candleSeries = chart.addCandlestickSeries({
      upColor:        '#22c55e',
      downColor:      '#ef4444',
      borderUpColor:  '#22c55e',
      borderDownColor:'#ef4444',
      wickUpColor:    '#22c55e',
      wickDownColor:  '#ef4444',
    })

    chartRef.current  = chart
    seriesRef.current = candleSeries

    // resize chart when window resizes
    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [])

  // update candle data whenever symbol or candles change
  useEffect(() => {
    if (!seriesRef.current || !candles?.length) return

    // lightweight-charts expects time as unix timestamp (seconds)
    const formatted = candles.map((c) => ({
      time:  Math.floor(new Date(c.timestamp).getTime() / 1000),
      open:  c.open,
      high:  c.high,
      low:   c.low,
      close: c.close,
    }))

    seriesRef.current.setData(formatted)
    chartRef.current.timeScale().fitContent()
  }, [candles, symbol])

  return (
    <div ref={containerRef} className="w-full rounded-lg overflow-hidden" />
  )
}
