"""
routes/ws.py

WebSocket endpoints for live price streaming and portfolio updates.

Now connected to the real simulation engine instead of random noise.
The engine pushes price ticks every second derived from historical
OHLCV candle replay. Each tick also includes the order book snapshot.
"""

import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """
    Tracks active WebSocket connections per symbol.
    The simulation engine holds a reference to this manager
    so it can push ticks to all subscribed clients.
    """

    def __init__(self):
        # symbol → list of active WebSocket connections
        self.subscriptions: dict[str, list[WebSocket]] = {}

    async def connect(self, symbol: str, websocket: WebSocket):
        await websocket.accept()
        if symbol not in self.subscriptions:
            self.subscriptions[symbol] = []
        self.subscriptions[symbol].append(websocket)

    def disconnect(self, symbol: str, websocket: WebSocket):
        if symbol in self.subscriptions:
            if websocket in self.subscriptions[symbol]:
                self.subscriptions[symbol].remove(websocket)
            if not self.subscriptions[symbol]:
                del self.subscriptions[symbol]

    async def send(self, websocket: WebSocket, data: dict):
        try:
            await websocket.send_text(json.dumps(data, default=str))
        except Exception:
            pass


# shared manager — the engine injects itself into this via set_ws_manager()
manager = ConnectionManager()


@router.websocket("/prices/{symbol}")
async def price_feed(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint for live price ticks.

    Clients connect here and receive a message every second containing:
      - ltp: last traded price (from historical candle replay)
      - change / change_pct: vs candle open
      - order_book: current bid/ask depth snapshot

    The simulation engine drives all the updates — this endpoint just
    registers the connection and keeps it alive. The engine broadcasts
    to all registered connections on every tick.

    Frontend usage:
        const ws = new WebSocket("ws://localhost:8000/ws/prices/RELIANCE")
        ws.onmessage = (e) => {
            const { ltp, change_pct, order_book } = JSON.parse(e.data)
        }
    """
    symbol = symbol.upper()
    await manager.connect(symbol, websocket)

    # send an immediate snapshot so the client has something to show
    # before the next engine tick fires
    try:
        from backend.simulation.engine import sim_engine
        current_price = sim_engine.get_current_price(symbol)

        if current_price is None:
            # symbol not in engine — no data available
            await websocket.send_text(json.dumps({
                "error": f"No simulation data for '{symbol}'. "
                         f"Make sure the CSV file exists in data/."
            }))
            await websocket.close()
            manager.disconnect(symbol, websocket)
            return

        # send initial snapshot immediately
        from backend.simulation.order_book import generate_order_book
        book = generate_order_book(symbol, current_price)

        await websocket.send_text(json.dumps({
            "symbol":     symbol,
            "ltp":        current_price,
            "change":     0.0,
            "change_pct": 0.0,
            "timestamp":  datetime.utcnow().isoformat(),
            "order_book": book,
        }, default=str))

        # keep the connection alive — engine handles all further updates
        # we just wait here until the client disconnects
        while True:
            try:
                # wait for a ping/pong or disconnect
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                # send a keepalive ping every 30s
                await websocket.send_text(json.dumps({"type": "ping"}))

    except WebSocketDisconnect:
        manager.disconnect(symbol, websocket)
    except Exception:
        manager.disconnect(symbol, websocket)


@router.websocket("/portfolio/{user_id}")
async def portfolio_feed(websocket: WebSocket, user_id: int):
    """
    WebSocket for portfolio value updates.

    Sends a portfolio summary every 5 seconds so the dashboard
    numbers stay fresh without requiring full page reloads.

    In a future iteration, the engine would push this whenever
    an order fills, making it event-driven rather than polling.
    """
    await websocket.accept()

    try:
        while True:
            # push portfolio summary on a timer
            # TODO: make event-driven when engine fills an order
            await websocket.send_text(json.dumps({
                "type":      "portfolio_update",
                "user_id":   user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message":   "refresh",  # tells frontend to re-fetch /api/portfolio/summary
            }))
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        pass
