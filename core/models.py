# SRP: data structures only — no logic, no validation
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


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
    BUY          = "BUY"
    SELL         = "SELL"
    HOLD         = "HOLD"
    FORCE_SELL   = "FORCE_SELL"
    PARTIAL_SELL = "PARTIAL_SELL"


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
