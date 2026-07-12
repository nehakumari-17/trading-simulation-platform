import asyncio
import json
import random
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.services.market_data import get_latest_price

router = APIRouter()


class ConnectionManager:
    """Tracks active WebSocket connections per symbol."""

    def __init__(self):
        self.subscriptions: dict[str, list[WebSocket]] = {}

    async def connect(self, symbol: str, websocket: WebSocket):
        await websocket.accept()
        if symbol not in self.subscriptions:
            self.subscriptions[symbol] = []
        self.subscriptions[symbol].append(websocket)

    def disconnect(self, symbol: str, websocket: WebSocket):
        if symbol in self.subscriptions:
            self.subscriptions[symbol].remove(websocket)
            if not self.subscriptions[symbol]:
                del self.subscriptions[symbol]

    async def send(self, websocket: WebSocket, data: dict):
        try:
            await websocket.send_text(json.dumps(data, default=str))
        except Exception:
            pass


manager = ConnectionManager()


@router.websocket("/prices/{symbol}")
async def price_feed(websocket: WebSocket, symbol: str):
    """
    Streams price ticks every second.
    Simulates small random movements on top of the last historical close.
    Will be replaced by the simulation engine later.

    Frontend usage:
        const ws = new WebSocket("ws://localhost:8000/ws/prices/RELIANCE")
        ws.onmessage = (e) => console.log(JSON.parse(e.data).ltp)
    """
    symbol = symbol.upper()
    await manager.connect(symbol, websocket)

    base_price = await get_latest_price(symbol)

    if base_price is None:
        await websocket.send_text(json.dumps({"error": f"No data found for '{symbol}'"}))
        await websocket.close()
        return

    current_price = base_price

    try:
        while True:
            change_pct    = random.uniform(-0.001, 0.001)
            current_price = round(current_price * (1 + change_pct), 2)
            current_price = max(current_price, base_price * 0.85)
            current_price = min(current_price, base_price * 1.15)

            change = round(current_price - base_price, 2)
            tick = {
                "symbol":     symbol,
                "ltp":        current_price,
                "change":     change,
                "change_pct": round((change / base_price) * 100, 2),
                "timestamp":  datetime.utcnow().isoformat(),
            }
            await manager.send(websocket, tick)
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        manager.disconnect(symbol, websocket)


@router.websocket("/portfolio/{user_id}")
async def portfolio_feed(websocket: WebSocket, user_id: int):
    """
    Sends portfolio heartbeats every 5 seconds.
    Will carry real portfolio update data once the simulation engine is added.
    """
    await websocket.accept()

    try:
        while True:
            await websocket.send_text(json.dumps({
                "type":      "heartbeat",
                "user_id":   user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message":   "portfolio stream active",
            }))
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        pass
