# backtest/backtest_runner.py
# SRP: replicates TradingAgent._execute_cycle() loop without sleep() or I/O side effects.
# Returns a BacktestResult computed from accumulated logger data and final portfolio state.

from dataclasses import replace as dc_replace

import config
from backtest.backtest_data_feeder import BacktestDataFeeder
from backtest.backtest_logger import BacktestLogger
from components.indicator_engine import IndicatorEngine
from components.portfolio import Portfolio
from components.risk_manager import RiskManager
from core.interfaces import BaseOrderExecutor, BaseStrategy
from core.models import Action, BacktestResult


class BacktestRunner:
    """Drives the backtest loop: feeder → indicator → risk → strategy → executor.

    Mirrors TradingAgent._execute_cycle() exactly (same priority order: risk > strategy)
    but replaces time.sleep() with nothing and returns BacktestResult instead of running
    indefinitely.
    """

    def __init__(
        self,
        feeder: BacktestDataFeeder,
        indicator: IndicatorEngine,
        strategy: BaseStrategy,
        risk_manager: RiskManager,
        portfolio: Portfolio,
        executor: BaseOrderExecutor,
        logger: BacktestLogger,
    ) -> None:
        self._feeder = feeder
        self._indicator = indicator
        self._strategy = strategy
        self._risk_manager = risk_manager
        self._portfolio = portfolio
        self._executor = executor
        self._logger = logger

    def run(self) -> BacktestResult:
        """Execute the full backtest and return aggregated statistics."""
        last_price: float = 0.0
        iteration: int = 0

        while self._feeder.has_next():
            candles = self._feeder.get_candles(count=config.CANDLE_COUNT)

            # Skip windows that are too short for indicator calculation
            if len(candles) < config.EMA_PERIOD:
                continue

            try:
                indicator_result = self._indicator.calculate(candles)
            except ValueError as exc:
                self._logger.log_error(f"Indicator error: {exc}")
                continue

            current_price = candles[-1].close
            candle_ts = candles[-1].timestamp  # use historical timestamp for trade records
            last_price = current_price
            iteration += 1

            # ── Progress print every 1000 candles ────────────────────────────
            if iteration % 1000 == 0:
                print(
                    f"Processing… {self._feeder.cursor:,}/{self._feeder.total:,} candles"
                )

            # ── Step 1: Risk check (highest priority) ─────────────────────────
            if self._portfolio.has_position():
                risk_signal = self._risk_manager.check(
                    current_price,
                    self._portfolio.get_avg_entry_price(),
                    rsi=indicator_result.rsi,
                    prev_rsi=indicator_result.prev_rsi,
                )

                if risk_signal is not None and risk_signal.action in (Action.FORCE_SELL, Action.SELL):
                    exit_action = risk_signal.action
                    trade = self._executor.execute(
                        action=exit_action,
                        price=current_price,
                        cash=self._portfolio.get_cash(),
                        btc=self._portfolio.get_btc_amount(),
                    )
                    trade = dc_replace(trade, timestamp=candle_ts)
                    self._portfolio.update(
                        exit_action, current_price, trade.amount, trade.fee
                    )
                    self._logger.log_signal(risk_signal)
                    self._logger.log_trade(trade)
                    self._logger.log_status(self._portfolio, current_price)
                    continue  # skip strategy — risk takes full priority this tick

            # ── Step 2: Strategy signal ────────────────────────────────────────
            signal = self._strategy.generate_signal(
                indicator_result, self._portfolio.get_position_count()
            )
            self._logger.log_signal(signal)

            if (
                signal.action == Action.BUY
                and self._portfolio.get_position_count() < config.MAX_POSITION_LEVELS
            ):
                trade = self._executor.execute(
                    action=Action.BUY,
                    price=current_price,
                    cash=self._portfolio.get_cash(),
                    btc=self._portfolio.get_btc_amount(),
                )
                trade = dc_replace(trade, timestamp=candle_ts)
                self._portfolio.update(Action.BUY, current_price, trade.amount, trade.fee)
                self._logger.log_trade(trade)

            elif signal.action == Action.SELL and self._portfolio.has_position():
                trade = self._executor.execute(
                    action=Action.SELL,
                    price=current_price,
                    cash=self._portfolio.get_cash(),
                    btc=self._portfolio.get_btc_amount(),
                )
                trade = dc_replace(trade, timestamp=candle_ts)
                self._portfolio.update(Action.SELL, current_price, trade.amount, trade.fee)
                self._logger.log_trade(trade)

            # ── Always record portfolio snapshot for MDD tracking ─────────────
            self._logger.log_status(self._portfolio, current_price)

        # ── Compute BacktestResult ─────────────────────────────────────────────
        final_total = (
            self._portfolio.get_total_value(last_price) if last_price > 0 else config.INITIAL_CASH
        )
        total_return = (final_total - config.INITIAL_CASH) / config.INITIAL_CASH * 100

        trade_records = self._logger.get_trade_records()
        total_trades = len(trade_records)
        win_count = sum(1 for t in trade_records if t["pnl_pct"] > 0)
        loss_count = total_trades - win_count
        win_rate = win_count / total_trades * 100 if total_trades > 0 else 0.0
        avg_hold_minutes = (
            sum(t["hold_minutes"] for t in trade_records) / total_trades
            if total_trades > 0
            else 0.0
        )

        mdd = self._compute_mdd(self._logger.get_portfolio_values())

        period_start = self._feeder.period_start
        period_end = self._feeder.period_end
        weeks = max(1.0, (period_end - period_start).days / 7)
        trades_per_week = total_trades / weeks

        return BacktestResult(
            period_start=period_start,
            period_end=period_end,
            total_trades=total_trades,
            win_count=win_count,
            loss_count=loss_count,
            win_rate=win_rate,
            total_return=total_return,
            mdd=mdd,
            avg_hold_minutes=avg_hold_minutes,
            trades_per_week=trades_per_week,
            final_total=final_total,
        )

    @staticmethod
    def _compute_mdd(portfolio_values: list[float]) -> float:
        """Maximum drawdown as a percentage from peak to trough."""
        if not portfolio_values:
            return 0.0
        peak = portfolio_values[0]
        mdd = 0.0
        for v in portfolio_values:
            if v > peak:
                peak = v
            if peak > 0:
                dd = (peak - v) / peak * 100
                if dd > mdd:
                    mdd = dd
        return mdd
