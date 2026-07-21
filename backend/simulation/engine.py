"""
simulation/engine.py

The main simulation loop — ties together all simulation components
and drives the historical data replay.

What it does every tick:
  1. Calls market_models.next_tick() for each active symbol
     → gets the next replayed price from historical data
  2. Rebuilds the order book snapshot from the new price
  3. Checks all PENDING limit orders in the DB
     → calls matching.match_order() for each one
     → fills triggered orders and updates portfolios
  4. Broadcasts price ticks + order book to WebSocket subscribers

It runs as a background asyncio task, started in main.py's lifespan.
The tick interval is controlled by settings.simulation_tick_interval.
"""

import asyncio
import json
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.models import Order, Trade, Portfolio, Position, OrderStatus, OrderSide, OrderType
from backend.simulation.market_models import (
    SymbolState,
    initialize_symbol,
    next_tick,
    get_current_candle,
    get_next_candle,
)
from backend.simulation.order_book import generate_order_book
from backend.simulation.matching   import match_order
from backend.utils.data_loader     import get_available_symbols


TRANSACTION_COST_RATE = 0.001  # 0.1% — same as execution.py


class SimulationEngine:
    """
    The simulation engine.

    Holds the replay state for every active symbol and drives
    the tick loop. One instance is created in main.py and shared
    across the application via app.state.sim_engine.
    """

    def __init__(self):
        # symbol → SymbolState (replay position, current price, etc.)
        self.symbol_states: dict[str, SymbolState] = {}

        # WebSocket connection manager — injected when engine starts
        # to avoid circular imports (ws.py imports engine)
        self.ws_manager = None

        self._running  = False
        self._task     = None

    def set_ws_manager(self, manager):
        """Called by ws.py to inject the WebSocket connection manager."""
        self.ws_manager = manager

    async def start(self):
        """
        Loads historical data for all available symbols and starts
        the background tick loop.
        """
        symbols = get_available_symbols()

        if not symbols:
            print("[engine] No symbols found in data/ folder — simulation not started")
            return

        # initialize replay state for each symbol
        for symbol in symbols:
            state = initialize_symbol(symbol)
            if state:
                self.symbol_states[symbol] = state

        print(f"[engine] Initialized {len(self.symbol_states)} symbols")

        self._running = True
        self._task    = asyncio.create_task(self._tick_loop())
        print(f"[engine] Simulation started (tick interval: {settings.simulation_tick_interval}s)")

    async def stop(self):
        """Gracefully stops the simulation loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("[engine] Simulation stopped")

    def get_current_price(self, symbol: str) -> float | None:
        """
        Returns the current replayed price for a symbol.
        Called by market_data service and order routes.
        """
        state = self.symbol_states.get(symbol.upper())
        if state:
            return state.current_price
        return None

    def get_order_book(self, symbol: str) -> dict | None:
        """Returns the current order book snapshot for a symbol."""
        state = self.symbol_states.get(symbol.upper())
        if not state:
            return None
        return generate_order_book(symbol, state.current_price)

    # ── Internal tick loop ────────────────────────────────────────────

    async def _tick_loop(self):
        """
        Main loop — runs every N seconds.
        On each tick, advances all symbols and processes pending orders.
        """
        while self._running:
            try:
                await self._process_tick()
            except Exception as e:
                # log but don't crash — simulation must keep running
                print(f"[engine] Tick error: {e}")

            await asyncio.sleep(settings.simulation_tick_interval)

    async def _process_tick(self):
        """
        One full simulation tick:
          1. Advance each symbol's price
          2. Check + fill any triggered limit orders
          3. Broadcast price updates via WebSocket
        """
        for symbol, state in self.symbol_states.items():
            # advance to next intraday price point
            tick = next_tick(state)

            # fill any triggered orders for this symbol
            # (only when we cross into a new candle — once per candle is enough
            #  because matching logic is based on candle H/L)
            if tick["is_new_candle"]:
                await self._process_pending_orders(symbol, state)

            # push price tick to WebSocket subscribers
            if self.ws_manager:
                await self._broadcast_tick(symbol, state, tick)

    async def _process_pending_orders(self, symbol: str, state: SymbolState):
        """
        Checks all PENDING orders for this symbol against the current candle.
        Fills any that are triggered based on matching rules.
        """
        current_candle = get_current_candle(state)
        next_candle    = get_next_candle(state)

        async with AsyncSessionLocal() as db:
            try:
                # fetch all pending orders for this symbol
                result = await db.execute(
                    select(Order).where(
                        Order.symbol == symbol,
                        Order.status == OrderStatus.PENDING,
                    )
                )
                pending_orders = result.scalars().all()

                for order in pending_orders:
                    fill = match_order(
                        symbol         = symbol,
                        order_type     = order.order_type.value,
                        side           = order.side.value,
                        quantity       = order.quantity,
                        limit_price    = order.price,
                        current_candle = current_candle,
                        next_candle    = next_candle,
                    )

                    if fill:
                        await self._fill_order(db, order, fill)

                await db.commit()

            except Exception as e:
                await db.rollback()
                print(f"[engine] Order processing error for {symbol}: {e}")

    async def _fill_order(self, db: AsyncSession, order: Order, fill: dict):
        """
        Executes a fill — updates the order status, creates a trade record,
        and updates the user's portfolio and position.
        """
        fill_price       = fill["fill_price"]
        slippage         = fill["slippage_amount"]
        trade_value      = fill_price * order.quantity
        transaction_cost = round(trade_value * TRANSACTION_COST_RATE, 2)

        # update order to FILLED
        order.status       = OrderStatus.FILLED
        order.filled_price = fill_price
        order.slippage     = slippage
        order.filled_at    = datetime.utcnow()

        # get the user's portfolio
        result    = await db.execute(
            select(Portfolio).where(Portfolio.user_id == order.user_id)
        )
        portfolio = result.scalar_one_or_none()
        if not portfolio:
            return

        pnl = 0.0

        if order.side == OrderSide.BUY:
            total_cost = trade_value + transaction_cost
            portfolio.cash_balance -= total_cost

            # update or create position
            pos_result = await db.execute(
                select(Position).where(
                    Position.portfolio_id == portfolio.id,
                    Position.symbol == order.symbol,
                )
            )
            position = pos_result.scalar_one_or_none()

            if position:
                total_qty              = position.quantity + order.quantity
                position.avg_buy_price = round(
                    (position.quantity * position.avg_buy_price + order.quantity * fill_price) / total_qty, 2
                )
                position.quantity      = total_qty
                position.current_price = fill_price
            else:
                db.add(Position(
                    portfolio_id  = portfolio.id,
                    symbol        = order.symbol,
                    quantity      = order.quantity,
                    avg_buy_price = fill_price,
                    current_price = fill_price,
                ))

        else:  # SELL
            proceeds = trade_value - transaction_cost
            portfolio.cash_balance += proceeds

            pos_result = await db.execute(
                select(Position).where(
                    Position.portfolio_id == portfolio.id,
                    Position.symbol == order.symbol,
                )
            )
            position = pos_result.scalar_one_or_none()

            if position:
                pnl = round(
                    (fill_price - position.avg_buy_price) * order.quantity - transaction_cost, 2
                )
                position.quantity      -= order.quantity
                position.current_price  = fill_price

                if position.quantity == 0:
                    await db.delete(position)

                portfolio.realized_pnl += pnl

        # create trade record
        db.add(Trade(
            user_id          = order.user_id,
            order_id         = order.id,
            symbol           = order.symbol,
            side             = order.side,
            quantity         = order.quantity,
            fill_price       = fill_price,
            slippage         = slippage,
            transaction_cost = transaction_cost,
            pnl              = pnl,
            executed_at      = datetime.utcnow(),
        ))

    async def _broadcast_tick(self, symbol: str, state: SymbolState, tick: dict):
        """
        Sends a price tick + order book snapshot to all WebSocket
        clients subscribed to this symbol.
        """
        # calculate change from the start of the current candle (open)
        candle     = get_current_candle(state)
        base_price = candle["open"]
        change     = round(state.current_price - base_price, 2)
        change_pct = round((change / base_price) * 100, 2) if base_price else 0

        # build order book for the current price
        book = generate_order_book(symbol, state.current_price)

        message = {
            "symbol":     symbol,
            "ltp":        state.current_price,
            "change":     change,
            "change_pct": change_pct,
            "timestamp":  datetime.utcnow().isoformat(),
            "order_book": book,
        }

        # push to all subscribed WebSocket connections
        subscribers = self.ws_manager.subscriptions.get(symbol, [])
        dead        = []

        for ws in subscribers:
            try:
                await ws.send_text(json.dumps(message, default=str))
            except Exception:
                dead.append(ws)

        # clean up disconnected clients
        for ws in dead:
            self.ws_manager.subscriptions[symbol].remove(ws)


# single shared instance — imported by main.py
sim_engine = SimulationEngine()
