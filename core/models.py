# SRP: data structures only — no logic, no validation
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


@dataclass
class CandleData:  # SRP: raw OHLCV value object
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float   # used as current price
    volume: float


@dataclass
class IndicatorResult:  # SRP: computed indicator snapshot
    rsi: float           # range: 0–100
    prev_rsi: float      # for crossover detection
    ema_200: float       # EMA(200) trend filter — price above = uptrend
    current_price: float # latest candle close; used for EMA trend comparison
    timestamp: datetime


class Action(Enum):  # OCP: extendable without modifying existing variants
    BUY        = "BUY"
    SELL       = "SELL"
    HOLD       = "HOLD"
    FORCE_SELL = "FORCE_SELL"


@dataclass
class Signal:  # SRP: strategy decision value object
    action: Action
    reason: str         # human-readable, e.g. "RSI 29.1 → 30 crossed up"
    timestamp: datetime


@dataclass
class TradeLog:  # SRP: immutable record of a single executed trade
    timestamp: datetime
    action: str              # one of: BUY / SELL / HOLD / FORCE_SELL / PARTIAL_SELL
    price: float
    amount: float            # BTC quantity transacted
    fee: float
    cash_after: float
    btc_after: float
    total_value: float
    reason: str
    sell_ratio: float = 0.0  # 1.0 for full sell, 0.5 for partial; 0.0 for BUY/HOLD


@dataclass
class BacktestResult:  # SRP: aggregated backtest statistics value object
    period_start: datetime
    period_end: datetime
    total_trades: int
    win_count: int
    loss_count: int
    win_rate: float          # percentage 0–100
    total_return: float      # percentage, signed
    mdd: float               # maximum drawdown percentage
    avg_hold_minutes: float
    trades_per_week: float
    final_total: float       # KRW
    # Exit-type breakdown — defaults allow BacktestRunner to construct without change;
    # BacktestLogger.print_report() fills these in-place before rendering.
    take_profit_2_count: int = 0    # 익절 (TP FORCE_SELL + RSI SELL)
    force_sell_count: int = 0       # 손절: Stop-loss FORCE_SELL 발생 횟수
    avg_pnl_take_profit_2: float = 0.0  # 익절 평균 손익률 (%)
    avg_pnl_force_sell: float = 0.0     # 손절 평균 손익률 (%)
