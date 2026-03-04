"""agent.py — TradingAgent: top-level orchestrator.

SOLID principles applied:
- SRP : TradingAgent only coordinates components; zero business logic lives here.
- OCP : New strategies/executors/risk rules can be swapped without touching this file.
- LSP : All dependencies are referenced via abstract base types (DataCollector, etc.).
- ISP : Each injected component exposes only the methods this class actually needs.
- DIP : All concrete implementations are injected from outside (constructor DI).
"""

import time

import config
from components.indicator_engine import IndicatorEngine
from components.logger import Logger
from components.portfolio import Portfolio
from components.risk_manager import RiskManager
from core.interfaces import BaseOrderExecutor, BaseStrategy, DataCollector
from core.models import Action


class TradingAgent:
    """Orchestrates the full trading cycle.

    Responsibilities (SRP):
    - Drive the main loop at a configurable interval.
    - Coordinate data → indicator → risk → strategy → execution flow.
    - Delegate all domain decisions to injected components.
    """

    def __init__(
        self,
        collector: DataCollector,
        indicator: IndicatorEngine,
        strategy: BaseStrategy,
        risk_manager: RiskManager,
        portfolio: Portfolio,
        executor: BaseOrderExecutor,
        logger: Logger,
    ) -> None:
        # DIP: store references via abstract types where possible; concrete where no ABC exists.
        self._collector    = collector
        self._indicator    = indicator
        self._strategy     = strategy
        self._risk_manager = risk_manager
        self._portfolio    = portfolio
        self._executor     = executor
        self._logger       = logger

        self._running: bool = False  # graceful-shutdown flag

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self) -> None:
        """Main loop: execute one trading cycle per INTERVAL_SEC seconds.

        Handles KeyboardInterrupt for clean shutdown (Ctrl-C).
        Wraps each cycle in a broad try/except so transient errors
        (network blips, API timeouts) never crash the agent.
        """
        self._running = True
        print("[Agent] Trading agent started. Press Ctrl-C to stop.")

        while self._running:
            try:
                self._execute_cycle()
            except KeyboardInterrupt:
                # Re-raise to the outer handler for clean shutdown logging.
                raise
            except Exception as exc:
                # SRP: error handling stays here; components never see each other's exceptions.
                self._logger.log_error(f"Cycle error: {exc}")

            try:
                time.sleep(config.INTERVAL_SEC)
            except KeyboardInterrupt:
                raise

    # ── Core cycle ────────────────────────────────────────────────────────────

    def _execute_cycle(self) -> None:
        """Execute one full decision cycle in strict priority order.

        Priority contract (intentional design):
        1. RiskManager ALWAYS takes precedence over Strategy.
        2. A FORCE_SELL exits immediately; strategy is never consulted.
        3. Strategy signals are evaluated only when no forced exit is needed.

        This ordering is not incidental — it is the core safety guarantee
        of the system (RiskManager > Strategy). The early return after
        FORCE_SELL is intentional and must not be refactored away.
        """
        # ── Step 1: Fetch candle data ─────────────────────────────────────
        # CANDLE_COUNT from config satisfies IndicatorEngine's minimum requirement
        # of RSI_PERIOD + 2 (validated by the assertion in config.py).
        candles = self._collector.get_candles(count=config.CANDLE_COUNT)

        # ── Step 2: Compute indicators ────────────────────────────────────
        indicator_result = self._indicator.calculate(candles)

        # ── Step 3: Derive current price from the latest candle ───────────
        current_price = candles[-1].close

        # ── Step 4: RISK CHECK (highest priority) ─────────────────────────
        # RiskManager is consulted before Strategy — it guards capital first.
        # DIP: agent calls the abstract check() interface, not a concrete rule.
        if self._portfolio.has_position():
            risk_signal = self._risk_manager.check(
                current_price, self._portfolio.get_entry_price()
            )

            if risk_signal is not None and risk_signal.action == Action.FORCE_SELL:
                # Execute forced exit; log; return immediately.
                # INTENTIONAL early return — Strategy must NOT override RiskManager.
                trade = self._executor.execute(
                    action=Action.FORCE_SELL,
                    price=current_price,
                    cash=self._portfolio.get_cash(),
                    btc=self._portfolio.get_btc_amount(),
                )
                self._portfolio.update(Action.FORCE_SELL, current_price, trade.amount, trade.fee)
                self._logger.log_trade(trade)
                self._logger.log_status(self._portfolio, current_price)
                return  # ← critical: skip strategy evaluation entirely

        # ── Step 5: STRATEGY SIGNAL (only if no FORCE_SELL triggered) ─────
        # SRP: strategy decides what action to take; agent only routes the result.
        signal = self._strategy.generate_signal(indicator_result)
        self._logger.log_signal(signal)

        if signal.action == Action.BUY and not self._portfolio.has_position():
            trade = self._executor.execute(
                action=Action.BUY,
                price=current_price,
                cash=self._portfolio.get_cash(),
                btc=self._portfolio.get_btc_amount(),
            )
            self._portfolio.update(Action.BUY, current_price, trade.amount, trade.fee)
            self._logger.log_trade(trade)

        elif signal.action == Action.SELL and self._portfolio.has_position():
            trade = self._executor.execute(
                action=Action.SELL,
                price=current_price,
                cash=self._portfolio.get_cash(),
                btc=self._portfolio.get_btc_amount(),
            )
            self._portfolio.update(Action.SELL, current_price, trade.amount, trade.fee)
            self._logger.log_trade(trade)

        # ── Step 6: Always log portfolio status at end of every cycle ─────
        self._logger.log_status(self._portfolio, current_price)
