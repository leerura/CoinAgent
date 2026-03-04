# SRP: this module has one job — evaluate price-based exit conditions
from datetime import datetime
from typing import Optional

from config import STOP_LOSS, TAKE_PROFIT_1, TAKE_PROFIT_2  # OCP: thresholds live in config, not here
from core.models import Action, Signal


class RiskManager:
    """Evaluates stop-loss and two-stage take-profit conditions only.

    Design notes:
    - SRP: judges price-based risk, nothing else (no indicators, no order logic)
    - DIP: depends on config constants and core models, not concrete components
    - Two-stage take-profit:
        Stage 1 (TAKE_PROFIT_1 = +2%): emit PARTIAL_SELL if not yet partially sold
        Stage 2 (TAKE_PROFIT_2 = +3%): emit FORCE_SELL (full exit)
    - Stop-loss (-2%): emit FORCE_SELL (full exit)
    """

    def check(
        self,
        current_price: float,
        avg_entry_price: Optional[float],
        partially_sold: bool = False,
    ) -> Optional[Signal]:
        # Guard: no active position → nothing to protect
        if not avg_entry_price:
            return None

        pnl_ratio = (current_price - avg_entry_price) / avg_entry_price
        pnl_pct = pnl_ratio * 100  # convert to % for human-readable reason

        if pnl_ratio <= STOP_LOSS:
            return Signal(
                action=Action.FORCE_SELL,
                reason=f"Stop-loss triggered: {pnl_pct:.2f}%",
                timestamp=datetime.now(),
            )

        # Stage 2: full exit at TAKE_PROFIT_2 (+3%)
        if pnl_ratio >= TAKE_PROFIT_2:
            return Signal(
                action=Action.FORCE_SELL,
                reason=f"Take-profit-2 triggered: {pnl_pct:.2f}%",
                timestamp=datetime.now(),
            )

        # Stage 1: partial exit at TAKE_PROFIT_1 (+2%) — fires only once per trade cycle
        if pnl_ratio >= TAKE_PROFIT_1 and not partially_sold:
            return Signal(
                action=Action.PARTIAL_SELL,
                reason=f"Take-profit-1 triggered: {pnl_pct:.2f}% (partial sell)",
                timestamp=datetime.now(),
            )

        # KISS: no signal needed — caller interprets None as "hold"
        return None
