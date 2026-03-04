# SRP: this module only handles logging — no business logic, no state mutation
# Standard library only: no colorlog, loguru, or other third-party deps
import logging
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

# Allow `python components/logger.py` to find project root packages (core, etc.)
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import MAX_POSITION_LEVELS
from core.models import Action, Signal, TradeLog

# Lazy import to avoid circular dependency — Portfolio is not in interfaces.py
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from components.portfolio import Portfolio

# ── ANSI color codes ──────────────────────────────────────────────────────────
_RESET  = "\033[0m"
_GREEN  = "\033[32m"
_RED    = "\033[31m"
_CYAN   = "\033[36m"
_BOLD   = "\033[1m"


def _action_color(action: str) -> str:
    """Map an action string to its ANSI color prefix."""
    if action in ("BUY",):
        return _GREEN
    if action in ("SELL", "FORCE_SELL", "PARTIAL_SELL"):
        return _RED
    return ""  # HOLD — no color


# ── Custom formatters ─────────────────────────────────────────────────────────

class _ConsoleFormatter(logging.Formatter):
    """Short timestamp (HH:MM:SS), color injected per-record via `color` extra."""

    def format(self, record: logging.LogRecord) -> str:
        ts    = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        color = getattr(record, "color", "")
        msg   = record.getMessage()
        return f"[{ts}] {color}{msg}{_RESET if color else ''}"


class _FileFormatter(logging.Formatter):
    """Full timestamp (YYYY-MM-DD HH:MM:SS), no ANSI codes."""

    def format(self, record: logging.LogRecord) -> str:
        ts  = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        msg = record.getMessage()
        return f"[{ts}] {msg}"


# ── Logger class ──────────────────────────────────────────────────────────────

class Logger:
    """Writes structured trading events to both console and a daily rotating file.

    Design decisions
    ----------------
    * Standard `logging` module — zero new dependencies, works everywhere.
    * A child logger (`trading`) is created so callers can adjust the root
      logger independently without affecting this component.
    * All formatting lives in dedicated Formatter subclasses (SRP).
    * Color is passed as a LogRecord `extra` so the file handler simply
      ignores it — no ANSI pollution in log files.
    """

    def __init__(self, log_dir: str = "logs") -> None:
        # Ensure log directory exists (idempotent)
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        self._logger = logging.getLogger("trading")
        self._logger.setLevel(logging.DEBUG)

        # Guard against duplicate handlers when Logger is re-instantiated
        if self._logger.handlers:
            self._logger.handlers.clear()

        # ── Console handler ───────────────────────────────────────────────
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(_ConsoleFormatter())
        self._logger.addHandler(console_handler)

        # ── File handler (daily rotation, keep 7 days) ────────────────────
        log_filename = log_path / f"trading_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = TimedRotatingFileHandler(
            filename=str(log_filename),
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(_FileFormatter())
        self._logger.addHandler(file_handler)

        # Prevent propagation to the root logger (avoids duplicate output)
        self._logger.propagate = False

    # ── Public interface ──────────────────────────────────────────────────────

    def log_signal(self, signal: Signal) -> None:
        action = signal.action.value
        msg    = f"[SIGNAL] {action} | {signal.reason}"
        color  = _action_color(action)
        self._logger.info(msg, extra={"color": color})

    def log_trade(self, trade: TradeLog) -> None:
        msg = (
            f"[TRADE ] {trade.action} | "
            f"price={trade.price:,.0f} | "
            f"amount={trade.amount:.8f} BTC | "
            f"fee={trade.fee:,.0f} KRW | "
            f"cash={trade.cash_after:,.0f} KRW | "
            f"total={trade.total_value:,.0f} KRW"
        )
        if trade.action in ("SELL", "FORCE_SELL", "PARTIAL_SELL"):
            msg += f" | sell_ratio={trade.sell_ratio:.1%}"
        if trade.reason:
            msg += f" | {trade.reason}"
        color = _action_color(trade.action)
        self._logger.info(msg, extra={"color": color})

    def log_error(self, message: str) -> None:
        msg = f"[ERROR ] {message}"
        self._logger.error(msg, extra={"color": f"{_BOLD}{_RED}"})

    def log_status(self, portfolio: "Portfolio", current_price: float) -> None:
        avg_entry     = portfolio.get_avg_entry_price()
        avg_entry_str = f"{avg_entry:,.0f}" if avg_entry is not None else "-"
        position_count = portfolio.get_position_count()
        total     = portfolio.get_total_value(current_price)
        win_rate  = portfolio.get_win_rate() * 100
        msg = (
            f"[STATUS] "
            f"cash={portfolio.get_cash():,.0f} KRW | "
            f"btc={portfolio.get_btc_amount():.8f} | "
            f"avg_entry={avg_entry_str} | "
            f"level={position_count}/{MAX_POSITION_LEVELS} | "
            f"total={total:,.0f} KRW | "
            f"win_rate={win_rate:.1f}%"
        )
        self._logger.info(msg, extra={"color": _CYAN})


# ── Manual smoke test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    from datetime import datetime
    from core.models import Action, Signal, TradeLog
    from components.portfolio import Portfolio

    logger = Logger(log_dir="logs")

    # 1) Signal
    buy_signal = Signal(
        action=Action.BUY,
        reason="RSI 29.1 → 30 상향 돌파",
        timestamp=datetime.now(),
    )
    logger.log_signal(buy_signal)

    sell_signal = Signal(
        action=Action.SELL,
        reason="RSI 71.3 → 70 하향 돌파",
        timestamp=datetime.now(),
    )
    logger.log_signal(sell_signal)

    hold_signal = Signal(
        action=Action.HOLD,
        reason="RSI 45 — 중립 구간",
        timestamp=datetime.now(),
    )
    logger.log_signal(hold_signal)

    # 2) Trade
    buy_trade = TradeLog(
        timestamp=datetime.now(),
        action="BUY",
        price=94_250_000.0,
        amount=0.00002123,
        fee=100.0,
        cash_after=79_900.0,
        btc_after=0.00002123,
        total_value=99_800.0,
        reason="RSI crossover",
    )
    logger.log_trade(buy_trade)

    sell_trade = TradeLog(
        timestamp=datetime.now(),
        action="SELL",
        price=97_000_000.0,
        amount=0.00002123,
        fee=103.0,
        cash_after=101_900.0,
        btc_after=0.0,
        total_value=101_900.0,
        reason="",
        sell_ratio=1.0,
    )
    logger.log_trade(sell_trade)

    partial_trade = TradeLog(
        timestamp=datetime.now(),
        action="PARTIAL_SELL",
        price=96_000_000.0,
        amount=0.00001061,
        fee=51.0,
        cash_after=90_900.0,
        btc_after=0.00001062,
        total_value=90_900.0 + 0.00001062 * 96_000_000.0,
        reason="Take-profit-1",
        sell_ratio=0.5,
    )
    logger.log_trade(partial_trade)

    # 3) Status
    portfolio = Portfolio(initial_cash=100_000.0)
    logger.log_status(portfolio, current_price=94_250_000.0)

    # 4) Error
    logger.log_error("Upbit API timeout")

    print("\n✓ Log file written to logs/trading_*.log")
