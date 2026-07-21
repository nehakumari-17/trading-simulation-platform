"""
main.py — FastAPI application entry point.

Starts the simulation engine on startup and wires all routes together.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import engine, Base
from backend.routes import auth, orders, portfolio, market_data, ws
from backend.routes import strategy
from backend.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created / verified.")

    # start the simulation engine
    from backend.simulation.engine import sim_engine
    from backend.routes.ws import manager as ws_manager

    # give the engine a reference to the WebSocket manager
    # so it can push ticks to connected clients
    sim_engine.set_ws_manager(ws_manager)
    await sim_engine.start()

    # expose the engine on app state so routes can access current prices
    app.state.sim_engine = sim_engine

    yield

    # shutdown
    await sim_engine.stop()
    print("Server shutting down.")


app = FastAPI(
    title="Trading Simulation Platform",
    description="A broker-style paper trading simulator with historical market replay.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allows the React frontend (port 3000 / 5173) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# mount all route groups
app.include_router(auth.router,        prefix="/api/auth",      tags=["Auth"])
app.include_router(orders.router,      prefix="/api/orders",    tags=["Orders"])
app.include_router(portfolio.router,   prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(market_data.router, prefix="/api/market",    tags=["Market Data"])
app.include_router(strategy.router,    prefix="/api/strategy",  tags=["Strategy"])
app.include_router(ws.router,          prefix="/ws",            tags=["WebSocket"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "message": "Trading Simulation Platform is running."}


@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "Welcome to the Trading Simulation Platform API.",
        "docs":    "Visit /docs to explore all available endpoints.",
    }
