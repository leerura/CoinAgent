# SRP: this module has one job — evaluate price-based exit conditions
from datetime import datetime
from typing import Optional

from config import STOP_LOSS, TAKE_PROFIT  # OCP: thresholds live in config, not here
from core.models import Action, Signal


class RiskManager:
    """Evaluates stop-loss and take-profit conditions only.

    Design notes:
    - SRP: judges price-based risk, nothing else (no indicators, no order logic)
    - DIP: depends on config constants and core models, not concrete components
    - YAGNI: no trailing stops, no partial exits — only what's specified
    """

    def check(self, current_price: float, entry_price: Optional[float]) -> Optional[Signal]:
        # Guard: no active position → nothing to protect
        if not entry_price:
            return None

        pnl_ratio = (current_price - entry_price) / entry_price
        pnl_pct = pnl_ratio * 100  # convert to % for human-readable reason

        if pnl_ratio <= STOP_LOSS:
            return Signal(
                action=Action.FORCE_SELL,
                reason=f"Stop-loss triggered: {pnl_pct:.2f}%",
                timestamp=datetime.now(),
            )

        if pnl_ratio >= TAKE_PROFIT:
            return Signal(
                action=Action.FORCE_SELL,
                reason=f"Take-profit triggered: {pnl_pct:.2f}%",
                timestamp=datetime.now(),
            )

        # KISS: no signal needed — caller interprets None as "hold"
        return None
