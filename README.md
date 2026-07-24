# Trading Simulation Platform

A web-based trading simulation platform that allows users to trade virtual stocks, test algorithmic trading strategies, and analyze portfolio performance using historical market data. The platform combines a modern React frontend with a FastAPI backend and a realistic market simulation engine.

---

## Project Overview

This project simulates a real trading environment where users can:

- Register and authenticate securely
- Trade using virtual money
- Place Market and Limit Orders
- Monitor portfolio performance
- Run algorithmic trading strategy backtests
- View live market replay using historical data
- Experience realistic order execution with slippage and risk checks

The platform is designed for learning algorithmic trading, quantitative finance, and market microstructure.

---

## Features

### Authentication

- User Registration
- User Login
- JWT Authentication
- Password Hashing (bcrypt)
- Protected APIs

### Trading

- Market Orders
- Limit Orders
- Order History
- Order Cancellation
- Portfolio Management
- Position Tracking

### Market Data

- Historical OHLCV Data
- 15 NSE Stocks
- Live Historical Replay
- Real-time Price Updates
- Market Watch

### Algorithmic Trading

Implemented Strategies:

- Moving Average Crossover
- RSI Strategy
- VWAP Strategy

Performance Metrics:

- Total Return
- Sharpe Ratio
- Win Rate
- Maximum Drawdown
- Profit Factor

### Simulation Engine

The simulation engine includes:

- Historical OHLCV replay
- Intraday price generation
- Candle-based order matching
- Volume-based slippage model
- Synthetic Limit Order Book
- Live WebSocket broadcasting

### Risk Management

- Position Size Validation
- Available Cash Check
- Exposure Validation
- Order Risk Checks

---

## Tech Stack

### Frontend

- React
- Vite
- React Router
- Axios
- Tailwind CSS
- WebSocket API
- Lucide React Icons

### Backend

- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- JWT Authentication
- bcrypt
- Uvicorn

### Data Processing

- Pandas
- NumPy
- yfinance

---

## Project Structure

```
trading-simulation-platform/

├── backend/
│   ├── routes/
│   ├── services/
│   ├── simulation/
│   ├── schemas/
│   ├── utils/
│   ├── models.py
│   ├── database.py
│   ├── config.py
│   └── main.py
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── context/
│   │   ├── services/
│   │   └── App.jsx
│
├── data/
│   ├── RELIANCE.csv
│   ├── TCS.csv
│   ├── INFY.csv
│   └── ...
│
├── download_data.py
└── README.md
```

---

## Database Tables

- users
- portfolios
- positions
- orders
- trades
- strategy_runs

---

## Simulation Workflow

```
Historical CSV Data
        │
        ▼
Market Replay Engine
        │
        ▼
Live Price Tick
        │
        ▼
Order Matching
        │
        ▼
Slippage Calculation
        │
        ▼
Portfolio Update
        │
        ▼
WebSocket Broadcast
        │
        ▼
React Frontend
```

---

## Trading Workflow

```
User
 │
 ▼
React Frontend
 │
 ▼
Axios API Request
 │
 ▼
FastAPI Backend
 │
 ▼
Risk Check
 │
 ▼
Order Matching
 │
 ▼
Slippage Model
 │
 ▼
Database Update
 │
 ▼
Portfolio Update
 │
 ▼
WebSocket Broadcast
```

---

## Historical Market Data

The platform currently includes approximately 5 years of historical daily OHLCV data for 15 NSE-listed stocks.

Example symbols:

- RELIANCE
- TCS
- INFY
- ICICIBANK
- HDFCBANK
- SBIN
- AXISBANK
- BAJFINANCE
- ITC
- MARUTI
- WIPRO
- SUNPHARMA
- ASIANPAINT
- KOTAKBANK
- HINDUNILVR

---

## REST API

### Authentication

```
POST /auth/register
POST /auth/login
GET  /auth/me
```

### Market

```
GET /market/quotes
GET /market/candles
GET /market/search
```

### Orders

```
POST /orders
GET /orders
DELETE /orders/{id}
```

### Portfolio

```
GET /portfolio
GET /portfolio/trades
```

### Strategy

```
POST /strategy/run
GET /strategy/history
```

---

## Running the Project

### Backend

```bash
cd trading-simulation-platform

backend\venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Backend runs at:

```
http://127.0.0.1:8000
```

Swagger Docs:

```
http://127.0.0.1:8000/docs
```

---

### Frontend

```bash
cd frontend

npm install

npm run dev
```

Frontend:

```
http://localhost:3000
```

---

## Future Improvements

- Multi-user market simulation
- Advanced limit order book
- Tick-level market replay
- Additional algorithmic trading strategies
- Paper trading mode
- Portfolio optimization
- Performance analytics dashboard
- Docker deployment
- PostgreSQL support
- Redis caching

---

## Research Concepts Implemented

- Historical Market Replay
- Limit Order Book (LOB)
- Price-Time Priority Matching
- Volume-based Slippage
- Risk Management
- Strategy Backtesting
- Market Microstructure
- Performance Evaluation

---

## Learning Outcomes

This project demonstrates practical implementation of:

- Full Stack Web Development
- REST APIs
- JWT Authentication
- Real-time WebSockets
- SQL Databases
- Financial Market Simulation
- Algorithmic Trading
- Quantitative Finance Concepts
- Portfolio Analytics
- Trading System Design

---

## License

This project is intended for educational and research purposes.