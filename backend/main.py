from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import engine, Base
from backend.routes import auth, orders, portfolio, market_data, ws
from backend.routes import strategy
from backend.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Everything inside the 'before yield' block runs on startup.
    Everything after yield runs on shutdown.

    On startup we just create the database tables if they don't exist yet.
    SQLAlchemy reads all the models from models.py and builds the tables
    automatically — you don't have to write any SQL yourself.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created / verified.")
    yield
    print("Server shutting down.")


app = FastAPI(
    title="Trading Simulation Platform",
    description="A broker-style paper trading simulator with realistic market models.",
    version="1.0.0",
    lifespan=lifespan,
)


# CORS
# CORS tells the browser it's okay for the frontend (running on a different port)
# to make requests to this backend.
# Without this, every API call from React would be blocked by the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#Routes
# Each router handles a group of related endpoints.
# The prefix is the URL path it lives under.

app.include_router(auth.router,        prefix="/api/auth",      tags=["Auth"])
app.include_router(orders.router,      prefix="/api/orders",    tags=["Orders"])
app.include_router(portfolio.router,   prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(market_data.router, prefix="/api/market",    tags=["Market Data"])
app.include_router(strategy.router,    prefix="/api/strategy",  tags=["Strategy"])
app.include_router(ws.router,          prefix="/ws",            tags=["WebSocket"])


#Health check
# A simple endpoint to confirm the server is running.
# Useful for checking if the backend is up before the frontend makes calls.
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "message": "Trading Simulation Platform is running."}


#Root
@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "Welcome to the Trading Simulation Platform API.",
        "docs":    "Visit /docs to explore all available endpoints.",
    }
