# backtest/backtest_logger.py
# SRP: silent logger for backtesting — prints only trade events; tracks stats for final report.
# Method signatures match components/logger.py so BacktestRunner can call them identically.

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from core.models import BacktestResult, Signal, TradeLog

if TYPE_CHECKING:
    from components.portfolio import Portfolio


class BacktestLogger:
    """Drop-in replacement for Logger during backtesting.

    Design choices:
    - log_signal / log_status are silent (no console spam per candle).
    - log_trade prints every executed trade (BUY / SELL / FORCE_SELL).
    - log_status silently records portfolio total_value for MDD computation.
    - Completed trades (SELL / FORCE_SELL) are recorded with hold duration and P&L.
    - print_report() accepts a BacktestResult and renders the final summary.
    """

    def __init__(self) -> None:
        # Internal position mirror (same logic as Logger's internal tracking)
        self._entry_timestamp: Optional[datetime] = None
        self._logger_btc: float = 0.0
        self._logger_avg_entry: Optional[float] = None

        # Completed trade records: list of dicts with pnl_pct and hold_minutes
        self._trade_records: list[dict] = []

        # Portfolio value series for MDD (one entry per log_status call)
        self._portfolio_values: list[float] = []

        # Exit-type breakdown tracking
        self._exit_records: list[dict] = []          # {exit_type, pnl_pct}
        self._last_signal_reason: str = ""           # cached from log_signal

    # ── Public interface — matches Logger method signatures ───────────────────

    def log_signal(self, signal: Signal) -> None:
        self._last_signal_reason = signal.reason     # cache for exit-type classification

    def log_trade(self, trade: TradeLog) -> None:
        # Print every non-zero trade event
        if trade.amount == 0:
            return

        line = (
            f"[TRADE ] {trade.action} | "
            f"ts={trade.timestamp.strftime('%Y-%m-%d %H:%M')} | "
            f"price={trade.price:,.0f} | "
            f"amount={trade.amount:.8f} BTC | "
            f"total={trade.total_value:,.0f} KRW"
        )
        if trade.action in ("SELL", "FORCE_SELL"):
            line += f" | sell_ratio={trade.sell_ratio:.1%}"
        print(line)

        # ── Mirror portfolio position for P&L / hold-duration tracking ───────
        if trade.action == "BUY":
            if self._entry_timestamp is None:
                self._entry_timestamp = trade.timestamp
            self._logger_avg_entry = trade.price
            self._logger_btc += trade.amount

        elif trade.action in ("SELL", "FORCE_SELL"):
            hold_minutes = 0.0
            pnl_pct = 0.0

            if self._entry_timestamp is not None:
                hold_minutes = (
                    trade.timestamp - self._entry_timestamp
                ).total_seconds() / 60

            if self._logger_avg_entry is not None and self._logger_avg_entry > 0:
                pnl_pct = (
                    (trade.price - self._logger_avg_entry) / self._logger_avg_entry * 100
                )

            self._trade_records.append(
                {
                    "entry_ts": self._entry_timestamp,
                    "exit_ts": trade.timestamp,
                    "hold_minutes": hold_minutes,
                    "pnl_pct": pnl_pct,
                    "action": trade.action,
                }
            )

            # ── Exit-type classification ──────────────────────────────────────
            reason = self._last_signal_reason
            if trade.action == "FORCE_SELL" and "Stop-loss" in reason:
                exit_type = "FORCE_SELL"
            else:
                # SELL (RSI crossover) or FORCE_SELL triggered by TP → both are TP2
                exit_type = "TP2"

            self._exit_records.append(
                {
                    "exit_type": exit_type,
                    "pnl_pct": pnl_pct,
                }
            )

            entry_str = (
                self._entry_timestamp.strftime("%Y-%m-%d %H:%M")
                if self._entry_timestamp
                else "-"
            )
            print(
                f"[EXIT  ] "
                f"entry={entry_str} | "
                f"exit={trade.timestamp.strftime('%Y-%m-%d %H:%M')} | "
                f"hold={hold_minutes:.0f}min | "
                f"pnl={pnl_pct:+.2f}%"
            )

            self._entry_timestamp = None
            self._logger_btc = 0.0
            self._logger_avg_entry = None

    def log_status(self, portfolio: "Portfolio", current_price: float) -> None:
        """Silent — records portfolio total value for MDD calculation."""
        self._portfolio_values.append(portfolio.get_total_value(current_price))

    def log_error(self, message: str) -> None:
        print(f"[ERROR ] {message}")

    # ── Data accessors for BacktestRunner ─────────────────────────────────────

    def get_trade_records(self) -> list[dict]:
        return self._trade_records

    def get_portfolio_values(self) -> list[float]:
        return self._portfolio_values

    # ── Final report ──────────────────────────────────────────────────────────

    def print_report(self, result: BacktestResult) -> None:
        period_days = (result.period_end - result.period_start).days
        n_weeks = period_days / 7

        # ── Populate breakdown fields in-place on result ──────────────────────
        tp2_records = [r for r in self._exit_records if r["exit_type"] == "TP2"]
        fs_records  = [r for r in self._exit_records if r["exit_type"] == "FORCE_SELL"]

        result.take_profit_2_count = len(tp2_records)
        result.force_sell_count    = len(fs_records)

        result.avg_pnl_take_profit_2 = (
            sum(r["pnl_pct"] for r in tp2_records) / len(tp2_records) if tp2_records else 0.0
        )
        result.avg_pnl_force_sell = (
            sum(r["pnl_pct"] for r in fs_records) / len(fs_records) if fs_records else 0.0
        )

        # ── Main report ───────────────────────────────────────────────────────
        print()
        print("========== BACKTEST RESULT ==========")
        print(
            f"기간        : "
            f"{result.period_start.strftime('%Y-%m-%d')} ~ "
            f"{result.period_end.strftime('%Y-%m-%d')} "
            f"({n_weeks:.1f}주)"
        )
        print(f"총 거래      : {result.total_trades}회")
        print(
            f"승률         : {result.win_rate:.1f}% "
            f"(승 {result.win_count} / 패 {result.loss_count})"
        )
        print(f"총 수익률    : {result.total_return:+.2f}%")
        print(f"최대 낙폭    : {result.mdd:.2f}%")
        print(f"평균 보유    : {result.avg_hold_minutes:.0f}분")
        print(f"주당 거래    : {result.trades_per_week:.1f}회")
        print(f"최종 잔고    : {result.final_total:,.0f} KRW")
        print("=====================================")

        # ── Trade Breakdown ───────────────────────────────────────────────────
        print()
        print("========== TRADE BREAKDOWN ==========")
        print(
            f"익절 (TP / RSI)   : {result.take_profit_2_count}회"
            f"  avg P&L {result.avg_pnl_take_profit_2:+.2f}%"
        )
        print(
            f"손절 (Stop-loss)  : {result.force_sell_count}회"
            f"  avg P&L {result.avg_pnl_force_sell:+.2f}%"
        )
        print("=====================================")
