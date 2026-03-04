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
    rsi: float          # range: 0–100
    prev_rsi: float     # for crossover detection
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
    action: str              # one of: BUY / SELL / HOLD / FORCE_SELL
    price: float
    amount: float            # BTC quantity
    fee: float
    cash_after: float
    btc_after: float
    total_value: float
    reason: str
