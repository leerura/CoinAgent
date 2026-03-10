# SRP: this module has one job — evaluate price-based exit conditions
from datetime import datetime
from typing import Optional

from config import RSI_OVERBOUGHT, STOP_LOSS, TAKE_PROFIT_2  # OCP: thresholds live in config, not here
from core.models import Action, Signal


class RiskManager:
    """Evaluates stop-loss, take-profit, and RSI-based exit conditions.

    Design notes:
    - SRP: judges price-based risk, nothing else (no order logic)
    - DIP: depends on config constants and core models, not concrete components
    - Priority order:
        1. Stop-loss (-1.5%): emit FORCE_SELL
        2. Take-profit (+3%): emit FORCE_SELL
        3. RSI cross-down below RSI_OVERBOUGHT with pnl >= 0: emit SELL
    """

    def check(
        self,
        current_price: float,
        avg_entry_price: Optional[float],
        partially_sold: bool = False,  # kept for interface compatibility, no longer used
        rsi: Optional[float] = None,
        prev_rsi: Optional[float] = None,
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

        if pnl_ratio >= TAKE_PROFIT_2:
            return Signal(
                action=Action.FORCE_SELL,
                reason=f"Take-profit triggered: {pnl_pct:.2f}%",
                timestamp=datetime.now(),
            )

        # RSI cross-down: RSI falls below RSI_OVERBOUGHT while in profit
        if (
            rsi is not None
            and prev_rsi is not None
            and prev_rsi > RSI_OVERBOUGHT
            and rsi <= RSI_OVERBOUGHT
            and pnl_ratio >= 0.0
        ):
            return Signal(
                action=Action.SELL,
                reason=f"RSI {prev_rsi:.1f} → {rsi:.1f} 하향 돌파 (기준: {RSI_OVERBOUGHT:.0f}), pnl={pnl_pct:+.2f}%",
                timestamp=datetime.now(),
            )

        # KISS: no signal needed — caller interprets None as "hold"
        return None
