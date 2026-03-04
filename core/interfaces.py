# SRP: abstract contracts only — no data structures, no logic
# ISP: each ABC defines exactly one responsibility
from abc import ABC, abstractmethod

from core.models import Action, CandleData, IndicatorResult, Signal, TradeLog


class BaseStrategy(ABC):  # OCP: new strategies extend without modifying this contract
    @abstractmethod
    def generate_signal(self, indicator: IndicatorResult) -> Signal:
        """Given indicator data, return a trading signal (BUY/SELL/HOLD)."""
        ...


class DataCollector(ABC):  # ISP: only candle-fetching responsibility
    @abstractmethod
    def get_candles(self, count: int) -> list[CandleData]:
        """Fetch the latest `count` candles. Returns list ordered oldest→newest."""
        ...


class BaseOrderExecutor(ABC):  # ISP: only order-execution responsibility
    @abstractmethod
    def execute(self, action: Action, price: float, cash: float, btc: float) -> TradeLog:
        """
        Execute an order given action type, current price, and current holdings.
        Returns a TradeLog capturing the result.
        """
        ...
